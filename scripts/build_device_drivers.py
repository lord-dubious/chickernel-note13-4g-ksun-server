#!/usr/bin/env python3
"""Build pinned sapphire drivers in mixed mode. Linux/WSL; no device commands."""
import argparse,hashlib,json,os,re,shutil,subprocess,tempfile
from pathlib import Path
import build
from verify_kernel import verify
from check_module_versions import compare

ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(args,**kw):
 print('+',' '.join(map(str,args)),flush=True)
 return subprocess.run(list(map(str,args)),check=True,**kw)
def output(args,**kw):return subprocess.check_output(list(map(str,args)),text=True,**kw)

def prepare_vendor(source):
 lock=json.loads((ROOT/'vendor-source-lock.json').read_text())
 assert output(['git','-C',source,'rev-parse','HEAD']).strip()==lock['commit']
 run(['git','-C',source,'diff','--cached','--quiet','HEAD'])
 # Upstream tracks generated dependency and CRC sidecars. Authenticate the
 # source separately; the CRC sidecars and corresponding objects are removed
 # before compilation below so only freshly computed versions can be used.
 paths=['--','.',':(exclude,glob)**/*.o.d',':(exclude,glob)**/*.o.symversions']
 with tempfile.TemporaryDirectory(prefix='sapphire-source-index-') as tmp:
  env=os.environ|{'GIT_INDEX_FILE':str(Path(tmp)/'index')}
  run(['git','-C',source,'read-tree','HEAD'],env=env)
  patches=[]
  for name,h in lock['patches'].items():
   p=(ROOT/name).resolve();assert p.is_relative_to(ROOT) and digest(p)==h,name
   run(['git','-C',source,'apply','--cached','--check',p],env=env)
   run(['git','-C',source,'apply','--cached',p],env=env);patches.append(p)
  expected=output(['git','-C',source,'diff','--cached','--binary','HEAD',*paths],env=env)
  actual=output(['git','-C',source,'diff','--binary','HEAD',*paths])
  if not actual:
   for p in patches:run(['git','-C',source,'apply',p])
   actual=output(['git','-C',source,'diff','--binary','HEAD',*paths])
  assert actual==expected,'Vendor source differs from the checksum-locked patch set'
 for name in output(['git','-C',source,'ls-files','--others','--exclude-standard']).splitlines():
  assert not (name.endswith(('.c','.h')) and not name.endswith('.mod.c')),'Untracked source input: '+name
 return lock

def module_files(root):
 order=root/'modules.order';assert order.is_file(),str(order)
 files=[]
 for name in order.read_text().splitlines():
  p=Path(name);p=p if p.is_absolute() else root/p;p=p.resolve()
  assert p.is_file() and p.is_relative_to(root.resolve()),str(p)
  files.append(p)
 return files

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['source','vendor','mmrm-test','gki','out','toolchain','dist']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--jobs',type=int,default=2);p.add_argument('--source-check-only',action='store_true');a=p.parse_args()
 assert a.jobs>0
 S=a.source.resolve();V=a.vendor.resolve();G=a.gki.resolve();O=a.out.resolve();D=a.dist.resolve();T=a.mmrm_test.resolve()
 assert not O.is_relative_to(S) and O!=G and not D.is_relative_to(S) and D!=O
 build.prepare_source(S);vendor_lock=prepare_vendor(V)
 test_lock=vendor_lock['additional_sources']['mmrm-driver-test']
 assert output(['git','-C',T,'rev-parse','HEAD']).strip()==test_lock['commit']
 assert not output(['git','-C',T,'diff','HEAD']).strip(),'Unrelated MMRM test source edits'
 if a.source_check_only:
  print('Pinned common, vendor and MMRM test sources verified.');return
 assert (G/'vmlinux').is_file() and (G/'vmlinux.symvers').is_file(),'Complete the GKI build first'
 assert (G/'arch/arm64/boot/Image').is_file()
 assert not D.exists() or not any(D.iterdir()),'Keep previous driver artifacts; choose an empty dist'
 O.mkdir(parents=True,exist_ok=True);D.mkdir(parents=True,exist_ok=True)
 for name in output(['git','-C',V,'ls-files','*.o.symversions']).splitlines():
  sidecar=(V/name).resolve();assert sidecar.is_relative_to(V)
  for generated in [sidecar,sidecar.with_suffix('')]:
   assert generated.is_relative_to(V) and not generated.is_symlink()
   if generated.exists():generated.unlink()
 env=os.environ.copy();env['PATH']=str(a.toolchain.resolve()/'bin')+':'+env['PATH']
 fragments=[S/'arch/arm64/configs/chickernel-variants/ksun.config']+[ROOT/'reference-source'/n for n in ['server.config','native-sapphire.config','thin-lto.config']]
 verify(G/'arch/arm64/boot/Image','image',fragments,G/'.config')
 fix=O/'preserve-filesystems.config';fix.write_text('CONFIG_NETWORK_FILESYSTEMS=y\n')
 requested=O/'requested.config'
 run(['bash',S/'scripts/kconfig/merge_config.sh','-m','-y',G/'.config',S/'arch/arm64/configs/vendor/bengal_GKI.config',ROOT/'reference-source/sapphire-drivers.config',*fragments[1:],fix],cwd=O,env=env|{'KCONFIG_CONFIG':str(requested)})
 make=['make','-C',S,'O='+str(O),'ARCH=arm64','LLVM=1','HOSTCC=gcc','HOSTCXX=g++','HOSTLD=g++','LOCALVERSION=','KBUILD_MIXED_TREE='+str(G),'VMLINUX_BTF_BASE='+str(G/'vmlinux')]
 run(make+['KCONFIG_ALLCONFIG='+str(requested),'alldefconfig'],env=env)
 config_check=verify(O/'.config','config',fragments)
 run(make+['-j'+str(a.jobs),'kernel/module.o','drivers/base/core.o','drivers/spi/spi.o'],env=env)
 core={f[1]:int(f[0],16) for l in (G/'vmlinux.symvers').read_text().splitlines() if len(f:=l.split())>=3}
 generated={}
 for n in ['kernel/module.o.symversions','drivers/base/core.o.symversions','drivers/spi/spi.o.symversions']:
  generated.update({n:int(c,16) for n,c in re.findall(r'__crc_(\w+)\s*=\s*(0x[0-9a-fA-F]+)',(O/n).read_text())})
 for n in ['module_layout','put_device','spi_setup','spi_sync']:assert generated[n]==core[n],n
 run(make+['-j'+str(a.jobs),'modules'],env=env)
 tables=[G/'vmlinux.symvers',O/'Module.symvers'];modules=module_files(O);receipts=[]
 def external(label,rel,options=(),providers=()):
  path=T if label=='mmrm_test' else V/rel
  # Fresh ELF link ensures previous split BTF cannot carry into this build.
  if (path/'modules.order').exists():
   for f in module_files(path):
    assert output(['git','-C',T if label=='mmrm_test' else V,'ls-files','--',str(f)]).strip()=='','Refuse to remove tracked module'
    f.unlink()
  extra=[V/n/'Module.symvers' for n in providers]
  assert all(f.is_file() and 'stock' not in f.name.lower() for f in extra)
  cmd=make+['M='+str(path),'-j'+str(a.jobs),'KERNEL_SRC='+str(S),'CONFIG_ARCH_KHAJE=y',*options]
  if extra:cmd+=['KBUILD_EXTRA_SYMBOLS='+' '.join(map(str,extra))]
  cmd+=['modules'];run(cmd,env=env)
  tables.append(path/'Module.symvers');modules.extend(module_files(path));receipts.append({'module':label,'command':list(map(str,cmd))})
 Q='qcom/opensource/';X='xiaomi/opensource/'
 external('mmrm',Q+'mmrm-driver',['CONFIG_QCOM_MMRM=m','MMRM_ROOT='+str(V/(Q+'mmrm-driver'))])
 external('mmrm_test','',['CONFIG_MSM_MMRM=m'],[Q+'mmrm-driver'])
 external('secure',Q+'securemsm-kernel',['SSG_MODULE_ROOT='+str(V/(Q+'securemsm-kernel'))])
 external('ipa',Q+'dataipa/drivers/platform/msm',['DATAIPA_ROOT='+str(V/(Q+'dataipa')),'BOARD_PLATFORM=bengal'])
 external('rmnet',Q+'datarmnet/core',['RMNET_CORE_ROOT='+str(V/(Q+'datarmnet/core')),'KCFLAGS=-I'+str(V/(Q+'datarmnet/core'))],[Q+'dataipa/drivers/platform/msm'])
 external('rmnet_wlan',Q+'datarmnet-ext/wlan',['KCFLAGS=-I'+str(V/(Q+'datarmnet/core'))],[Q+'datarmnet/core'])
 for n in ['miev','lct_tp','bootinfo','swinfo','perf_helper','mi_wmark','binder_prio','millet','st21nfc','mi_memory','battery_auth','sc8541','bq25960','xiaomi_fp','cp_qc30','pd_policy_manager']:external(n,X+n)
 external('nxp-nci',X+'nxp-nci',providers=[Q+'securemsm-kernel'])
 external('xiaomi_touch',X+'xiaomi_touch',providers=[X+'miev'])
 external('focaltech',X+'focaltech',providers=[X+'lct_tp',X+'xiaomi_touch'])
 external('xm_smart_chg',X+'xm_smart_chg',providers=[X+'miev'])
 external('display',Q+'display-drivers',['DISPLAY_ROOT='+str(V/(Q+'display-drivers')),'CONFIG_DRM_MSM=m'],[X+'miev'])
 external('gpu',Q+'graphics-kernel',['KGSL_PATH='+str(V/(Q+'graphics-kernel'))])
 external('video',Q+'video-driver',['VIDEO_ROOT='+str(V/(Q+'video-driver')),'MODNAME=msm_video','BOARD_PLATFORM=bengal'],[Q+'mmrm-driver'])
 external('camera',Q+'camera-kernel',['CAMERA_KERNEL_ROOT='+str(V/(Q+'camera-kernel')),'KERNEL_ROOT='+str(S),'MODNAME=camera','BOARD_PLATFORM=bengal'],[Q+'mmrm-driver'])
 external('audio',Q+'audio-kernel',['AUDIO_ROOT='+str(V/(Q+'audio-kernel')),'MODNAME=audio_dlkm','CONFIG_ARCH_BENGAL=y'])
 external('wlan_platform',Q+'wlan/platform',['WLAN_PLATFORM_ROOT='+str(V/(Q+'wlan/platform')),'CONFIG_CNSS_OUT_OF_TREE=y','CONFIG_ICNSS2=m','CONFIG_ICNSS2_QMI=y','CONFIG_CNSS_GENL=m','CONFIG_WCNSS_MEM_PRE_ALLOC=m','CONFIG_CNSS_UTILS=m','CONFIG_CNSS_QMI_SVC=m'],[Q+'securemsm-kernel'])
 external('bt',Q+'bt-kernel',['BT_ROOT='+str(V/(Q+'bt-kernel')),'BT_KERNEL_ROOT='+str(V/(Q+'bt-kernel')),'CONFIG_MSM_BT_POWER=m','CONFIG_BTFM_SLIM=m','CONFIG_I2C_RTC6226_QCA=m'],[Q+'wlan/platform'])
 external('wlan',Q+'wlan/qcacld-3.0',['KCFLAGS=-DCFG80211_SINGLE_NETDEV_MULTI_LINK_SUPPORT','CONFIG_CNSS_GENL=m','WLAN_CTRL_NAME=wlan','WLAN_ROOT='+str(V/(Q+'wlan/qcacld-3.0')),'WLAN_COMMON_ROOT=cmn','WLAN_COMMON_INC='+str(V/(Q+'wlan/qca-wifi-host-cmn')),'WLAN_FW_API='+str(V/(Q+'wlan/fw-api')),'WLAN_PROFILE=adrastea','MODNAME=wlan','DEVNAME=wlan','CONFIG_QCA_CLD_WLAN=m','CONFIG_ICNSS2=m','CONFIG_CNSS_OUT_OF_TREE=y','WLAN_PLATFORM_INC='+str(V/(Q+'wlan/platform/inc'))],[Q+'wlan/platform',Q+'datarmnet-ext/wlan'])
 exports={};owners={}
 for table in tables:
  for line in table.read_text().splitlines():
   f=line.split()
   if len(f)<3:continue
   crc=int(f[0],16);n=f[1];owner=f[2]
   if n in exports:assert exports[n]==crc and owners[n]==owner,('Conflicting export provider',n)
   exports[n]=crc;owners[n]=owner
 files=[];target=D/'modules';target.mkdir()
 for path in sorted(set(modules)):
  imports={n:int(c,16) for c,n in (line.split() for line in output(['modprobe','--show-modversions',path]).splitlines())};assert imports
  check=compare(exports,imports);assert not check['mismatches'] and not check['unresolved'],(str(path),check)
  name='qca_cld3_wlan.ko' if path.name=='wlan.ko' else path.name;dest=target/name;assert not dest.exists(),name
  run([a.toolchain.resolve()/'bin/llvm-strip','--strip-debug','-o',dest,path])
  files.append({'source':str(path),'file':name,'sha256':digest(dest),'source_sha256':digest(path),'bytes':dest.stat().st_size,**check})
 report={'scope':'Build and imported-symbol checks only; no phone operations or hardware-validation claim','kernel_image_sha256':digest(G/'arch/arm64/boot/Image'),'core_symvers_sha256':digest(G/'vmlinux.symvers'),'btf_base_sha256':digest(G/'vmlinux'),'vendor_source':vendor_lock,'config_check':config_check,'commands':receipts,'modules':files}
 (D/'driver-build-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
 print('Built and checked',len(files),'modules; device runtime remains untested.')

if __name__=='__main__':main()
