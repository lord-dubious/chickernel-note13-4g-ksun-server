#!/usr/bin/env python3
"""Offline sapphire boot/driver/recovery packaging. Never writes phone devices."""
from pathlib import Path
import argparse,subprocess,hashlib,json,shutil,tempfile,re,struct,uuid
from verify_kernel import read_config

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cpio_entries(p):
 data=Path(p).read_bytes();pos=0;entries={}
 while pos+110<=len(data):
  assert data[pos:pos+6] in (b'070701',b'070702'),('CPIO magic',pos)
  f=[int(data[pos+6+i*8:pos+14+i*8],16) for i in range(13)]
  n=data[pos+110:pos+110+f[11]-1].decode();pos=(pos+110+f[11]+3)&~3
  if n=='TRAILER!!!':break
  assert not n.startswith('/') and '..' not in Path(n).parts,n
  entries[n]={'mode':f[1],'data':data[pos:pos+f[6]]};pos=(pos+f[6]+3)&~3
 return entries

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--task',type=Path,required=True);p.add_argument('--build-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--candidate',type=Path);p.add_argument('--evidence-tag',default='extm-');p.add_argument('--stage-name',default='driver-stage-extm');a=p.parse_args()
 R=a.task.resolve();B=a.build_root.resolve();out=a.output.resolve()
 assert not out.exists(),'Output must be new; previous packages are retained'
 prefix='redmi-'+a.evidence_tag;candidate=a.candidate.resolve() if a.candidate else R/'outputs/chickernel-server-extm-candidate'
 cov=json.loads((R/'outputs'/(prefix+'driver-coverage.json')).read_text());audit=json.loads((R/'outputs'/(prefix+'rebuilt-module-compatibility.json')).read_text());cal=json.loads((R/'outputs'/(prefix+'battery-calibration-comparison.json')).read_text())
 assert cov['missing_count']==0 and audit['failing_modules']==0
 assert all(x['identical'] for x in cal.values()),'Battery calibration differs from device backup'
 cfg=(candidate/'kernel.config').read_text()
 for flag in ['CONFIG_EROFS_FS=y','CONFIG_EROFS_FS_ZIP=y','CONFIG_EROFS_FS_SECURITY=y','CONFIG_SWAP=y','CONFIG_ZRAM_WRITEBACK=y','CONFIG_MIUI_ZRAM_MEMORY_TRACKING=y']:
  assert flag+'\n' in cfg,flag
 core=candidate/'Image';assert sha(core)==audit['kernel_image_sha256']==cov['kernel_image_sha256']
 assert read_config(core,'image')==cfg,'Image and external config differ'
 bootbackup=R/'outputs/redmi-phone-backup-2026-11-15';bootman=json.loads((bootbackup/'backup-manifest.json').read_text())
 dlkmbackup=R/'outputs/redmi-dlkm-backup-2026-11-16';dlkmman=json.loads((dlkmbackup/'backup-manifest.json').read_text())
 originals={n:(bootbackup/d['file'],d) for n,d in bootman['partitions'].items()};originals.update({n:(dlkmbackup/d['file'],d) for n,d in dlkmman['partitions'].items()})
 for n in ['boot_b','vendor_boot_b','recovery_b','vendor_dlkm_b','system_dlkm_b','init_boot_b','vbmeta_b']:
  f,d=originals[n];assert d['verified'] and sha(f)==d['sha256'],n
 assert struct.unpack_from('>I',originals['vbmeta_b'][0].read_bytes(),120)[0]==3,'Requires existing disabled AVB state; never changes vbmeta'
 out.mkdir(parents=True);W=Path(tempfile.mkdtemp(prefix='sapphire-package-',dir=B));T=R/'work/boot-tools/magiskboot'
 def run(cmd,cwd=None,allowed=(0,)):
  r=subprocess.run(list(map(str,cmd)),cwd=cwd,capture_output=True,text=True)
  if r.returncode not in allowed:raise RuntimeError(str(cmd)+'\n'+r.stdout+r.stderr)
  return r.stdout+r.stderr
 stage_dir=(B/a.stage_name).resolve();assert stage_dir.is_relative_to(B)
 stage=json.loads((stage_dir/'manifest.json').read_text());pool=stage_dir/'modules'
 byname={v['name'].replace('-','_'):k for k,v in stage.items()}
 selected={v['file'] for v in cov['modules'].values() if v['status']=='rebuilt'}
 while True:
  extra={byname[d.replace('-','_')] for n in selected for d in stage[n]['depends'] if d}
  if extra<=selected:break
  selected|=extra
 for n in selected:assert sha(pool/n)==stage[n]['sha256'],n
 builtins={n for n,x in cov['modules'].items() if x['status']=='built_into_candidate'}
 def load_filter(data):
  lines=data.decode().splitlines();kept=[]
  for line in lines:
   t=line.strip()
   if not t or t.startswith('#'):kept.append(line);continue
   key=Path(t).stem.replace('-','_')
   if key in builtins:continue
   assert t in selected,('Unaccounted loader entry',t)
   kept.append(line)
  return ('\n'.join(kept)+'\n').encode()
 # Use normal depmod output. AOSP libmodprobe resolves relative entries
 # against its selected directory; vendor filenames are retained.
 release='5.15.189-chickernel-stable-7-ksun-server';root=W/'depmod-root';mods=root/'lib/modules'/release;mods.mkdir(parents=True)
 for n in sorted(selected):shutil.copy2(pool/n,mods/n)
 (mods/'modules.order').write_text(''.join(n+'\n' for n in sorted(selected)))
 (mods/'modules.builtin').write_text(''.join(cov['modules'][n]['provider']+'\n' for n in sorted(builtins)))
 (mods/'modules.builtin.modinfo').write_bytes(b'')
 run(['depmod','-b',root,release])
 metadata={n:(mods/n).read_bytes() for n in ['modules.dep','modules.alias','modules.softdep','modules.order','modules.builtin','modules.symbols','modules.devname'] if (mods/n).exists()}
 # Preserve all non-module partition files and existing blocklists.
 vendor=W/'vendor-root';system=W/'system-root';vendor.mkdir();system.mkdir()
 run(['debugfs','-R','rdump / '+str(vendor),originals['vendor_dlkm_b'][0]])
 run(['debugfs','-R','rdump / '+str(system),originals['system_dlkm_b'][0]])
 vm=vendor/'lib/modules';sm=system/'lib/modules/5.15.94';assert vm.is_dir() and sm.is_dir()
 for base in [vm,sm]:
  for f in base.iterdir():
   if f.is_file() and (f.name.endswith('.ko') or f.name in metadata or f.name.endswith('.bin') or (base==sm and f.name.startswith('modules.'))):f.unlink()
 for n in sorted(selected):shutil.copy2(pool/n,vm/n)
 for n,data in metadata.items():(vm/n).write_bytes(data)
 (vm/'modules.load').write_bytes(load_filter((vm/'modules.load').read_bytes()))
 # Both stock system_dlkm modules are already compiled into the Image.
 for n in ['modules.load','modules.dep','modules.alias','modules.softdep','modules.order']:(sm/n).write_bytes(b'')
 (sm/'modules.builtin').write_bytes(metadata['modules.builtin'])
 contexts=W/'vendor-file-contexts';contexts.write_text('/vendor_dlkm(/.*)? u:object_r:vendor_file:s0\n/vendor_dlkm/etc(/.*)? u:object_r:vendor_configs_file:s0\n')
 for f in vendor.rglob('*'):
  if f.is_dir():f.chmod(0o755)
  elif f.is_file():f.chmod(0o644)
 erofs=out/'vendor_dlkm_b.img'
 run(['mkfs.erofs','-b4096','-C4096','-zlz4hc,12','-E','legacy-compress,force-inode-compact','--all-root','-T0','-U',str(uuid.UUID(sha(core)[:32])),'--mount-point=/vendor_dlkm','--file-contexts='+str(contexts),erofs,vendor])
 raw_size=erofs.stat().st_size;assert raw_size<=originals['vendor_dlkm_b'][1]['bytes']
 extract=W/'vendor-roundtrip';run(['fsck.erofs','--extract='+str(extract),'--no-preserve',erofs])
 for f in vendor.rglob('*'):
  if f.is_file():assert (extract/f.relative_to(vendor)).is_file() and sha(f)==sha(extract/f.relative_to(vendor)),str(f)
 with erofs.open('ab') as f:f.truncate(originals['vendor_dlkm_b'][1]['bytes'])
 # Modify the small original ext4 system_dlkm image offline, retaining its
 # filesystem and all unrelated inode metadata.
 image=out/'system_dlkm_b.img';shutil.copy2(originals['system_dlkm_b'][0],image);commands=[]
 original_sm=(B/'package-baseline/system/lib/modules/5.15.94');assert original_sm.is_dir()
 for f in original_sm.iterdir():
  if f.is_file():commands.append('rm /lib/modules/5.15.94/'+f.name)
 label=W/'system-label';label.write_bytes(b'u:object_r:system_dlkm_file:s0\0')
 for f in sorted(sm.iterdir()):
  if not f.is_file():continue
  target='/lib/modules/5.15.94/'+f.name
  commands.extend(['write '+str(f)+' '+target,'set_inode_field '+target+' mode 0100644','ea_set -f '+str(label)+' '+target+' security.selinux'])
 cmd=W/'debugfs.commands';cmd.write_text('\n'.join(commands)+'\n');log=run(['debugfs','-w','-f',cmd,image]);(W/'debugfs.log').write_text(log)
 assert not re.search(r'(Could not|File not found|not enough|Usage:|while |Invalid argument)',log,re.I),log
 run(['e2fsck','-fn',image])
 syscheck=W/'system-roundtrip';syscheck.mkdir();run(['debugfs','-R','rdump / '+str(syscheck),image])
 assert not list(syscheck.rglob('*.ko')),'Old system modules remain'
 for f in system.rglob('*'):
  if f.is_file():assert sha(f)==sha(syscheck/f.relative_to(system)),str(f)
 # Preserve original headers, Magisk init_boot, DTB, bootconfig, recovery
 # binaries and filesystem content. Only driver payloads and one fstab
 # filesystem type change are intended in these ramdisks.
 checks={};replacement_hashes={};phone_recovery_load=None;recovery_other_board_modules=[]
 for n in ['boot_b','vendor_boot_b','recovery_b']:
  d=W/n;d.mkdir();run([T,'unpack','-h',originals[n][0]],cwd=d,allowed=(3,) if n=='vendor_boot_b' else (0,))
  preserved={f.name:sha(f) for f in d.iterdir() if f.is_file() and f.name in ['header','dtb','bootconfig']}
  if n=='boot_b':shutil.copy2(core,d/'kernel')
  else:
   ramdisks=list(d.rglob('*.cpio'));assert len(ramdisks)==1
   ram=ramdisks[0];before=cpio_entries(ram)
   if n=='vendor_boot_b':phone_recovery_load=before['lib/modules/modules.load.recovery']['data']
   base='lib/modules/' if n=='vendor_boot_b' else 'vendor/lib/modules/1.1/'
   old=[name for name,e in before.items() if name.startswith(base) and (name.endswith('.ko') or Path(name).name in metadata or name.endswith('.bin'))]
   ops=['rm '+name for name in old];expected={}
   for file in sorted(selected):
    name=base+file;ops.append('add 0644 '+name+' '+str(pool/file));expected[name]=sha(pool/file)
   for file,data in metadata.items():
    f=d/file;f.write_bytes(data);name=base+file;ops.append('add 0644 '+name+' '+str(f));expected[name]=sha(f)
   for name,e in before.items():
    if name.startswith(base) and Path(name).name.startswith('modules.load'):
     data=e['data']
     if n=='recovery_b':
      # The installed recovery is unified with other Redmi boards. Its
      # legacy load list includes their chargers, touch and clock modules.
      # Use this phone's real first-stage recovery list, retain applicable
      # legacy entries, and explicitly include its touch support chain.
      assert phone_recovery_load is not None
      lines=load_filter(phone_recovery_load).decode().splitlines()
      for item in data.decode().splitlines():
       item=item.strip()
       if not item or item.startswith('#'):continue
       if item in selected:lines.append(item)
       elif Path(item).stem.replace('-','_') not in builtins:recovery_other_board_modules.append(item)
      lines+=['miev.ko','lct_tp.ko','xiaomi_touch_game.ko','focaltech_ts_i2c.ko','msm_kgsl.ko']
      data=('\n'.join(dict.fromkeys(lines))+'\n').encode()
     f=d/('filtered-'+Path(name).name);f.write_bytes(load_filter(data));ops.append('add 0644 '+name+' '+str(f));expected[name]=sha(f)
    elif n=='vendor_boot_b' and 'fstab' in name and e['mode']&0o170000==0o100000:
     lines=e['data'].decode().splitlines(True);changed=0;new=[]
     for line in lines:
      cols=line.split()
      if len(cols)>=5 and cols[0]=='vendor_dlkm' and cols[1]=='/vendor_dlkm':
       assert cols[2]=='ext4';cols[2]='erofs';cols[3]='ro';line='\t'.join(cols)+'\n';changed+=1
      new.append(line)
     assert changed==1,('Unexpected fstab',name)
     f=d/('fstab-'+str(len(expected)));f.write_text(''.join(new));ops.append('add '+format(e['mode']&0o7777,'04o')+' '+name+' '+str(f));expected[name]=sha(f)
   run([T,'cpio',ram,*ops],cwd=d)
   after=cpio_entries(ram)
   for name,e in before.items():
    if name not in old and name not in expected:assert name in after and after[name]==e,('Unrelated ramdisk entry changed',n,name)
   for name,h in expected.items():assert hashlib.sha256(after[name]['data']).hexdigest()==h
   assert all(name in expected for name in after if name.endswith('.ko')),('Unreplaced recovery/module copy',n)
   replacement_hashes[n]=expected
  # Repack in a clean directory; scratch files must not become boot sections.
  clean=W/(n+'-repack');clean.mkdir()
  for f in d.iterdir():
   if f.name in ['kernel','kernel_dtb','ramdisk.cpio','vendor_ramdisk','second','dtb','extra','recovery_dtbo','bootconfig','header']:
    shutil.copytree(f,clean/f.name) if f.is_dir() else shutil.copy2(f,clean/f.name)
  dest=out/(n+'.img');run([T,'repack',originals[n][0],dest],cwd=clean)
  assert dest.stat().st_size<=originals[n][1]['bytes']
  with dest.open('ab') as f:f.truncate(originals[n][1]['bytes'])
  verify=W/(n+'-verify');verify.mkdir();run([T,'unpack','-h',dest],cwd=verify,allowed=(3,) if n=='vendor_boot_b' else (0,))
  for file,h in preserved.items():assert sha(verify/file)==h,('Boot metadata changed',n,file)
  if n=='boot_b':assert sha(verify/'kernel')==sha(core)
  else:
   rd=list(verify.rglob('*.cpio'));assert len(rd)==1;entries=cpio_entries(rd[0])
   for name,h in replacement_hashes[n].items():assert hashlib.sha256(entries[name]['data']).hexdigest()==h
  checks[n]={'preserved':preserved,'roundtrip':True}
 manifest={'status':'OFFLINE_PREPARED_NOT_INSTALLED','device':'sapphire','slot':'b','kernel_image_sha256':sha(core),'release':release,'replacement_modules':len(selected),'symbol_audit_modules':audit['rebuilt_modules'],'coverage':{k:v for k,v in cov.items() if k!='modules'},'vendor_dlkm_format':'erofs-lz4','vendor_dlkm_filesystem_bytes':raw_size,'partition_sizes_unchanged':True,'init_boot_unchanged':True,'existing_vbmeta_flags':3,'vbmeta_changed':False,'recovery_binaries_unchanged':True,'recovery_other_board_modules_excluded':sorted(set(recovery_other_board_modules)),'boot_roundtrip_checks':checks,'work_directory':str(W),'images':{},'runtime_validation':'Not run. Requires recovery preflight, installation and hardware/Docker checks.'}
 for n in ['boot_b','vendor_boot_b','recovery_b','vendor_dlkm_b','system_dlkm_b']:
  f=out/(n+'.img');manifest['images'][n]={'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f),'original':originals[n][1]}
 (out/'package-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 (out/'SHA256SUMS.txt').write_text(''.join(v['sha256']+'  '+v['file']+'\n' for v in manifest['images'].values()))
 print(json.dumps({k:v for k,v in manifest.items() if k not in ['images','boot_roundtrip_checks']},indent=2))

if __name__=='__main__':main()
