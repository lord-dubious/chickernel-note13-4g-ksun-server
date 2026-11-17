#include <errno.h>
#include <fcntl.h>
#include <linux/loop.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

int main(int argc, char **argv) {
    struct loop_info64 info;
    struct stat st;
    const char *prefix = "/dev/block/loop";
    const char *backing = "/data/per_boot/codex_extm_probe.backing";
    int autoclear = 0;
    if (argc == 3 || argc == 4) {
        backing = argv[2];
        if (strcmp(backing, "/data/per_boot/zram_swap") && strcmp(backing, "/data/per_boot/codex_extm_probe.backing")) return 2;
        if (argc == 4) {
            if (strcmp(argv[3], "--autoclear")) return 2;
            autoclear = 1;
        }
    } else if (argc != 2) return 2;
    if (strncmp(argv[1], prefix, strlen(prefix))) return 2;
    const char *p = argv[1] + strlen(prefix);
    if (!*p) return 2;
    for (; *p; p++) if (*p < '0' || *p > '9') return 2;
    if (stat(backing, &st) || !S_ISREG(st.st_mode)) return 3;
    int fd = open(argv[1], O_RDWR | O_CLOEXEC);
    if (fd < 0) { perror("open owned loop"); return 4; }
    memset(&info, 0, sizeof(info));
    if (ioctl(fd, LOOP_GET_STATUS64, &info) || info.lo_inode != st.st_ino ||
        info.lo_device != st.st_dev ||
        strncmp((const char *)info.lo_file_name, backing, LO_NAME_SIZE)) {
        fprintf(stderr, "Loop does not match owned probe backing file\n");
        close(fd); return 5;
    }
    if (autoclear) {
        info.lo_flags |= LO_FLAGS_AUTOCLEAR;
        if (ioctl(fd, LOOP_SET_STATUS64, &info)) {
            perror("set owned loop autoclear"); close(fd); return 6;
        }
    }
    if (ioctl(fd, LOOP_SET_BLOCK_SIZE, 4096)) {
        perror("set owned loop block size"); close(fd); return 6;
    }
    if (ioctl(fd, LOOP_SET_DIRECT_IO, 1)) {
        perror("enable direct I/O"); close(fd); return 6;
    }
    if (ioctl(fd, LOOP_GET_STATUS64, &info) || !(info.lo_flags & LO_FLAGS_DIRECT_IO)) {
        fprintf(stderr, "Direct I/O readback failed\n"); close(fd); return 7;
    }
    if (autoclear && !(info.lo_flags & LO_FLAGS_AUTOCLEAR)) {
        fputs("Autoclear readback failed\n", stderr); close(fd); return 8;
    }
    close(fd);
    puts("owned_loop_direct_io=enabled");
    if (autoclear) puts("owned_loop_autoclear=enabled");
    return 0;
}
