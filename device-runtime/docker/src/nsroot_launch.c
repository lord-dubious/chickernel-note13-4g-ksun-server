#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <unistd.h>

int main(int argc, char **argv) {
    const char *root="/data/local/codex-native-docker/rootfs";
    char current[128], init[128];
    const char *parent=getenv("SAPPHIRE_SERVER_PARENT_MNT");
    if ((argc!=2 && argc!=3) || strcmp(argv[1],root) || getuid()!=0 || !parent) return 2;
    if (argc==3 && strcmp(argv[2],"--probe")) return 2;
    ssize_t n=readlink("/proc/self/ns/mnt",current,sizeof(current)-1);
    if (n<0) return 3;
    current[n]=0;
    n=readlink("/proc/1/ns/mnt",init,sizeof(init)-1);
    if (n<0) return 3;
    init[n]=0;
    if (!strcmp(current,parent) || !strcmp(current,init)) {
        fputs("Refusing to change the caller or Android init mount namespace\n",stderr); return 4;
    }
    if (mount(NULL,"/",NULL,MS_REC|MS_PRIVATE,NULL) || chdir(root)) {
        perror("private namespace preparation"); return 5;
    }
    // Cover the private namespace's root, not just a subdirectory chroot.
    // Android's setns() resets fs.root to the namespace root. A subdirectory
    // chroot leaves runc exec looking at Android despite correct namespaces.
    // This only moves mounts; it never deletes old-root files.
    if (mount(root,"/",NULL,MS_MOVE,NULL) || chroot(".") || chdir("/")) {
        perror("private namespace root switch"); return 6;
    }
    if (argc==3) {
        execl("/bin/sh","sh","-c","echo NSROOT_PROBE_READY; exec /bin/busybox sleep 15",(char *)NULL);
    } else {
        execl("/usr/local/bin/dockerd","dockerd","--config-file=/etc/docker/daemon.json",(char *)NULL);
    }
    perror("exec namespace workload"); return 7;
}
