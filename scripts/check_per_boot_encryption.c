/* Read-only AArch64 Android/Linux probe. No libc, keys or device writes. */
typedef unsigned long u64;
static long call3(long number, long a, long b, long c)
{
    register long x8 __asm__("x8") = number;
    register long x0 __asm__("x0") = a;
    register long x1 __asm__("x1") = b;
    register long x2 __asm__("x2") = c;
    __asm__ volatile("svc 0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2) : "memory");
    return x0;
}
static void say(const char *s)
{
    u64 n = 0;
    while (s[n]) n++;
    call3(64, 1, (long)s, (long)n);
}
__attribute__((noreturn)) void _start(void)
{
    /* openat(AT_FDCWD, path, O_RDONLY | O_DIRECTORY); no creation flag. */
    long fd = call3(56, -100, (long)"/data/per_boot", 65536);
    long status;
    u64 flags = 0;
    if (fd < 0) {
        say("per_boot_directory=unavailable\n");
        status = 2;
    } else {
        /* FS_IOC_GETFLAGS for native AArch64; inspect FS_ENCRYPT_FL only. */
        long result = call3(29, fd, 0x80086601UL, (long)&flags);
        call3(57, fd, 0, 0);
        if (result < 0) {
            say("per_boot_encryption=not_verified\n");
            status = 3;
        } else if (flags & 0x800UL) {
            say("per_boot_encryption=present\n");
            status = 0;
        } else {
            say("per_boot_encryption=absent\n");
            status = 4;
        }
    }
    call3(93, status, 0, 0);
    for (;;) { }
}
