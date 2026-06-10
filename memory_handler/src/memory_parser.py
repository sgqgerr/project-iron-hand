import logging
import json
import re
import redis as r

class MemoryParser():

    KERNEL_PROC_NAMES = {
        "kthreadd", "kworker", "ksoftirqd", "migration", "rcu_sched",
        "watchdog", "kdevtmpfs", "netns", "khungtaskd", "oom_reaper",
        "writeback", "kcompactd0"
    }

    LEGITIMATE_PARENTS = {
        "sshd": {"systemd", "init", "sshd"},
        "bash": {"sshd", "login", "su", "sudo", "bash", "sh", "terminal"},
        "sh": {"sshd", "login", "su", "sudo", "bash", "sh"},
        "python3": {"bash", "sh", "cron", "systemd"},
        "python": {"bash", "sh", "cron", "systemd"},
        "cron": {"systemd", "init"},
        "systemd": {""},
        "su": {"bash", "sh"},
        "sudo": {"bash", "sh"},
    }

    PRIVATE_PREFIXES = (
        "192.168.", "10.", "172.16.", "172.17.", "172.18.", "172.19.",
        "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
        "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.",
        "127.", "::1", ""
    )

    KNOWN_MODULES = {
        "ext4", "mbcache", "jbd2", "crc16", "dm_mod", "dm_crypt", "aes_x86_64",
        "crypto_simd", "cryptd", "glue_helper", "xfs", "libcrc32c", "btrfs",
        "zstd_compress", "tcp_bbr", "nf_conntrack", "nf_nat", "iptable_nat",
        "ip6table_nat", "iptable_filter", "ip6table_filter", "nvidia", "nvidia_drm",
        "nvidia_uvm", "nvidia_modeset", "e1000e", "igb", "ixgbe", "ahci", "libahci",
        "usbhid", "hid_generic", "hid", "usb_storage", "drm", "drm_kms_helper",
        "ttm", "virtio_net", "virtio_blk", "virtio_pci", "overlay", "br_netfilter", "veth"
    }

    OBFUSCATION_RE = re.compile(
        r'[A-Za-z0-9+/]{50,}={0,2}|eval\s+\$\(|echo\s+.+\|\s*(ba)?sh|base64\s+(--decode|-d)|\|\s*base64|xxd\s+-r'
    )

    BASH_SUSPICIOUS_RE = re.compile(
        r'(curl|wget).+\|\s*(ba)?sh|chmod\s+\+x|(/tmp/|/dev/shm/|/var/tmp/)|bash\s+-i\s+>&\s*/dev/tcp/|(base64|xxd)\s+(-d|--decode)|python.+-c\s+["\']import socket'
    )

    HOUR_RE = re.compile(r'(\d{2}):\d{2}:\d{2}')

    def __init__(self , memory_path : str , to_redis : bool , case_id : str):

        self.memory_path = memory_path

        self.to_redis = to_redis

        self.case_id = case_id

    def _get_redis(self) -> r.Redis:

        return r.Redis(host='localhost',
                       port=6379,
                       db=0,
                       decode_responses=True)

    def _load_plugin_results(self , plugin : str) -> list[str]:

        raw : str | None = self._get_redis().get(f"vol3:{self.case_id}:{plugin}") # type: ignore[assignment]

        if not raw:

            return []

        try:

            data = json.loads(raw)

            if isinstance(data , list):

                return [str(item) for item in data]

            return str(data).splitlines()

        except json.decoder.JSONDecodeError:

            return raw.splitlines()

    def _parse_pslist(self , lines : list[str]) -> dict[int,dict]:

        processes : dict[int,dict] = {}

        for line in lines :

            parts = line.split()

            if len(parts) < 4 or parts == "PID":

                continue

            try:

                pid = int(parts[0])
                ppid = int(parts[1])
                comm = parts[2].lower()
                uid = int(parts[3])

                hour_match = self.HOUR_RE.match(comm)
                match = int(hour_match.group(1)) if hour_match else 0

                processes[pid] = {
                    "ppid" : ppid,
                    "comm" : comm,
                    "uid" : uid,
                    "hour" : hour_match.group(2) if hour_match else 0
                }

            except ValueError:

                continue

        return processes




    def _extract_wrong_parent(self , lines : list[str]) -> bool:

        processes = self._parse_pslist(lines)

        for pid , proc in processes.items():

            comm = proc["comm"]

            if comm not in self.LEGITIMATE_PARENTS:

                continue

            if comm in self.KERNEL_PROC_NAMES or pid <= 2:

                continue

            parent      = processes.get(proc["ppid"], {})

            parent_comm = parent.get("comm", "unknown")

            allowed     = self.LEGITIMATE_PARENTS[comm]

            if parent_comm not in allowed:

                return True

        return False


    def _extract_encoded_cmd(self, lines: list[str]) -> bool:

        for line in lines :

            parts = line.split()

            if len(parts) < 4 or parts == "PID":

                continue

            cmd = "".join(parts[1:])

            if self.OBFUSCATION_RE.match(cmd):

                return True

        return False

    def _extract_memory_injection(self , lines : list[str]) -> bool:

        for line in lines :

            parts = line.split()

            if len(parts) < 4 or parts == "PID":

                continue

            perms = parts[3].lower()

            filename = parts[4] if len(parts) > 4 else "-"

            has_rwx = "r" in perms and "w" in perms and "x" in perms

            no_file = filename.strip() in ("-", "", "N/A", "none")

            if has_rwx and no_file:

                return True

        return False


    def _extract_external_connection(self , lines : list[str]) -> bool:

        active_states = {"ESTABLISHED", "SYN_SENT", "CLOSE_WAIT"}

        for line in lines:

            parts = line.split()

            if len(parts) < 5 or parts[0] == "PID":

                continue

            foreign = parts[3]

            state = parts[4].upper()

            if state not in active_states:

                continue

            remote_ip = foreign.split(":")[0]

            if not remote_ip.startswith(self.PRIVATE_PREFIXES):

                return True

        return False

    def _extract_suspicious_kernel_module(self, lines: list[str]) -> bool:

        for line in lines:

            parts = line.split()

            if len(parts) < 1 or parts[0] == "Name":

                continue

            name = parts[0].lower().strip()

            base_name = re.split(r'[_\-]\d', name)[0]

            if name not in self.KNOWN_MODULES and base_name not in self.KNOWN_MODULES:

                return True

        return False

    def _extract_suspicious_bash_cmd(self, lines: list[str]) -> bool:

        for line in lines:

            parts = line.split()

            if len(parts) < 2 or parts[0] == "PID":

                continue

            cmd = " ".join(parts[1:])

            if self.BASH_SUSPICIOUS_RE.search(cmd):

                return True

        return False

    def _extract_root_process_from_user(self, lines: list[str]) -> bool:

        processes = self._parse_pslist(lines)

        for pid, proc in processes.items():

            if proc["uid"] != 0:

                continue

            if proc["comm"] in self.KERNEL_PROC_NAMES or pid <= 2:

                continue

            parent = processes.get(proc["ppid"], {})

            parent_comm = parent.get("comm", "unknown")

            if parent_comm not in self.LEGITIMATE_ROOT_PARENTS:

                return True

        return False

    def _extract_night_creation(self, lines: list[str]) -> bool:

        processes = self._parse_pslist(lines)

        for pid, proc in processes.items():

            if proc["comm"] in self.KERNEL_PROC_NAMES or pid <= 2:

                continue

            if 0 <= proc["hour"] <= 5:

                return True

        return False

    def parse(self) -> dict:

        pslist = self._load_plugin_results("pslist")

        bash = self._load_plugin_results("bash")

        netstat = self._load_plugin_results("netstat")

        lsmod = self._load_plugin_results("lsmod")

        malfind = self._load_plugin_results("malfind")

        cmdline = self._load_plugin_results("cmdline")

        features = {
            "wrong_parent": self._extract_wrong_parent(pslist),
            "encoded_cmd": self._extract_encoded_cmd(cmdline),
            "memory_injection": self._extract_memory_injection(malfind),
            "external_connection": self._extract_external_connection(netstat),
            "suspicious_kernel_module": self._extract_suspicious_kernel_module(lsmod),
            "suspicious_bash_cmd": self._extract_suspicious_bash_cmd(bash),
            "root_process_from_user": self._extract_root_process_from_user(pslist),
            "night_creation": self._extract_night_creation(pslist),
        }

        logging.info(f"[{self.case_id}] Memory features: {features}")

        if self.to_redis:
            self._get_redis().set(
                f"artifact:memory:{self.case_id}",
                json.dumps(features),
                ex=7200,
            )

        return {"case_id": self.case_id, "features": features}