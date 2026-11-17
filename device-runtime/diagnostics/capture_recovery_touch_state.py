"""Read-only TWRP touch/power snapshots. No coordinates, PINs or firmware writes."""
import argparse,json,shutil,subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--serial',required=True)
p.add_argument('--label',required=True,choices=['awake','locked','after-wake'])
args=p.parse_args()
R=Path(__file__).resolve().parents[1]
local=R/'work/platform-tools-current/platform-tools/adb.exe'
adb=str(local) if local.exists() else shutil.which('adb')
if not adb:raise SystemExit('ADB not found')
A=[adb,'-s',args.serial]
def read(command):
 r=subprocess.run(A+['shell',command],capture_output=True,text=True,timeout=12)
 return {'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
assert read('getprop ro.twrp.boot')['stdout'].strip()=='1','Recovery-only diagnostic; Android was not changed'
out={'label':args.label,'identity':read('uname -r; getprop ro.twrp.version; cat /proc/uptime')}
commands={
 'interrupts':"grep -i -E 'fts|focal' /proc/interrupts",
 'read_only_driver_state':"for f in /sys/bus/i2c/devices/1-0038/fts_irq /sys/bus/i2c/devices/1-0038/fts_driver_info /sys/bus/i2c/devices/1-0038/power/runtime_status; do if [ -r \"$f\" ]; then echo \"$f\"; cat \"$f\"; fi; done",
 'panel_brightness':"for f in /sys/class/backlight/*/brightness /sys/class/graphics/fb0/blank; do if [ -r \"$f\" ]; then echo \"$f\"; cat \"$f\"; fi; done",
 'filtered_driver_log':"dmesg | grep -i -E 'fts_ts_suspend|fts_ts_resume|fts_ts_panel_notifier_callback|irq_depth|touch buff is 0xff|panel_event.*(blank|unblank)' | tail -65",
}
for name,command in commands.items():out[name]=read(command)
dest=R/'outputs'/('redmi-recovery-touch-'+args.label+'.json')
dest.write_text(json.dumps(out,indent=2))
print(dest)
