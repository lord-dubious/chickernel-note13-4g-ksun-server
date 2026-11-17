#include <fcntl.h>
#include <linux/fscrypt.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(void) {
    struct fscrypt_get_policy_ex_arg policy;
    struct fscrypt_get_key_status_arg status;
    unsigned char reference[FSCRYPT_KEY_IDENTIFIER_SIZE];
    int ref=open("/data/unencrypted/per_boot_ref",O_RDONLY|O_CLOEXEC);
    if (ref<0) { perror("open public per-boot key reference"); return 2; }
    ssize_t n=read(ref,reference,sizeof(reference));close(ref);
    if (n!=(ssize_t)sizeof(reference)) return 3;
    int fd=open("/data/per_boot",O_RDONLY|O_DIRECTORY|O_CLOEXEC);
    if (fd<0) return 4;
    memset(&policy,0,sizeof(policy));policy.policy_size=sizeof(policy.policy);
    if (ioctl(fd,FS_IOC_GET_ENCRYPTION_POLICY_EX,&policy)) {perror("get policy");return 5;}
    if (policy.policy.v2.version!=FSCRYPT_POLICY_V2) return 6;
    printf("policy_version=%u flags=%u contents_mode=%u filenames_mode=%u\n",policy.policy.v2.version,policy.policy.v2.flags,policy.policy.v2.contents_encryption_mode,policy.policy.v2.filenames_encryption_mode);
    memset(&status,0,sizeof(status));status.key_spec.type=FSCRYPT_KEY_SPEC_TYPE_IDENTIFIER;
    memcpy(status.key_spec.u.identifier,policy.policy.v2.master_key_identifier,sizeof(reference));
    if (ioctl(fd,FS_IOC_GET_ENCRYPTION_KEY_STATUS,&status)) {perror("old key status");return 7;}
    unsigned int directory_status=status.status;
    int matches=memcmp(reference,policy.policy.v2.master_key_identifier,sizeof(reference))==0;
    printf("directory_key_status=%u\n",status.status);
    printf("directory_matches_current_boot_reference=%s\n",memcmp(reference,policy.policy.v2.master_key_identifier,sizeof(reference)) ? "no" : "yes");
    memset(&status,0,sizeof(status));status.key_spec.type=FSCRYPT_KEY_SPEC_TYPE_IDENTIFIER;
    memcpy(status.key_spec.u.identifier,reference,sizeof(reference));
    if (ioctl(fd,FS_IOC_GET_ENCRYPTION_KEY_STATUS,&status)) {perror("current key status");return 8;}
    printf("current_boot_key_status=%u\n",status.status);
    close(fd);
    return matches && directory_status==FSCRYPT_KEY_STATUS_PRESENT && status.status==FSCRYPT_KEY_STATUS_PRESENT ? 0 : 1;
}
