import logging
import redis as r
import re
import datetime as dt
import json


class LogsParser:

    def __init__(self , log_path, to_redis):

        self.log_path = log_path

        self.to_redis = to_redis

    def _get_redis(self) -> r.Redis:

        return r.Redis(host='localhost',
                       port=6379,
                       decode_responses=True)


    def _count_failed_logins(self , lines : list[str]) -> int:

        count = 0

        #TODO : Improve patterns later

        patterns = [
            r"Failed password",
            r"authentication failure",
            r"Invalid user",
            r"FAILED LOGIN",
        ]

        for line in lines:
            for pattern in patterns:

                if re.search(line, pattern, re.IGNORECASE):

                    count += 1

                    break

        return count

    def _detect_brute_force(self,
                            lines : list[str],
                            time_threshold : int = 10,
                            window_seconds : int = 60) -> bool:

        failed_timestamps = []

        time_pattern = re.compile(r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})")

        for line in lines:

            # TODO : Improve patterns later

            is_failed = any(p in line for p in [
                r"Failed password",
                r"authentication failure",
                r"Invalid user",
                r"FAILED LOGIN",
            ])

            if not is_failed:

                continue

            time_match = time_pattern.search(line)

            if not time_match:

                continue

            try :

                ts_str = time_match.group(1)

                ts = dt.strptime(ts_str, f"2024 {ts_str}", "%Y %b %d %H:%M:%S")

                failed_timestamps.append(ts)

            except ValueError:

                continue

            if len(failed_timestamps) < time_threshold:

                return False

            failed_timestamps.sort()

            for i in range(len(failed_timestamps) - time_threshold + 1):

                window = failed_timestamps[i:i+time_threshold]

                if window[-1] -window[0] <= window_seconds:

                    return True

            return False

    def _detect_shh_login(self, lines : list[str]) -> bool:

        # TODO : Improve patterns later

        patterns = [r"Accepted\s+(password|publickey)\s+for\s+root",
                    r"session opened for user root"]

        for line in lines:

            for pattern in patterns:

                if re.search(pattern, line, re.IGNORECASE):

                    return True

        return False

    def _detect_new_systemd_service(self , lines : list[str]) -> bool:

        # TODO : Improve patterns later

        patterns = [
            r"systemd\[\d+\]:\s+Created\s+.+\.service",
            r"systemd\[\d+\]:\s+Started\s+.+\.service",
            r"systemd\[\d+\]:\s+Loaded\s+.+\.service",
        ]

        # TODO : Improve patterns later

        whitelist = [
            "snapd", "apt", "update", "upgrade",
            "cron", "ssh", "network", "systemd-"
        ]

        for line in lines:

            for pattern in patterns:

                if re.search(pattern , line, re.IGNORECASE):

                    is_whitelisted = any(w in line.lower() for w in whitelist)

                    if is_whitelisted:

                        return True

        return False

    def _detect_log_tampering(self , lines : list[str] , gap_threshold_minutes : int = 30) -> bool:

        # TODO : Improve patterns later

        tampering_signs = [
            r"log file turned over",
            r"wtmp begins",
            r"BEGIN PGP",
            r"logrotate",
        ]

        for line in lines:

            for sign in tampering_signs:

                if re.search(sign, line, re.IGNORECASE):

                    return True

        time_pattern = re.compile(r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2})")

        timestamps = []

        for line in lines:

            time_match = re.search(time_pattern, line, re.IGNORECASE)

            if time_match:

                try:

                    ts = dt.strptime(f"2024 {time_match.group(1)}", "%Y %b %d %H:%M:%S")

                    timestamps.append(ts.timestamp())

                except ValueError:

                    continue


        if len(timestamps) < 2:

            return False


        timestamps.sort()

        for i in range(1 , len(timestamps)):

            gap_minutes = (timestamps[i] - timestamps[i-1]) / 60

            if gap_minutes < gap_threshold_minutes:

                return True

    def _save_to_redis(self) -> None:

        r = self._get_redis()

        main_key = f"artifacts:logs:{self.case_id}"

        r.set(main_key, json.dumps(self.features), ex = 7200)

        for i , (feature_name , feature_val) in enumerate(self.features.items()):

            if feature_name in ["count_failed_logins" , "brute_force",
                                "shh_login", "new_systemd_service",
                                "log_tampering"]:

                artifact_id = f"log:{feature_name}:{self.case_id[:4]}"

                r.set(
                    f"artifact_id : {artifact_id}",
                    json.dumps(
                        {

                            "feature" : feature_name,
                            "value" : feature_val,
                            "source" : "auth.log"

                        }
                    ),

                    ex=7200

                )

        logging.info(f"Successfully saved to Redis {main_key}...")

    def parse_log_file(self , log_path : str, to_redis : bool) -> dict:

        with open(log_path, "r", encoding = "utf-8" , errors = "ignore") as f:

            lines = f.readlines()

        logging.info(f"Parsing log file : {log_path} , {len(lines)} lines...")

        count_failed_logins = self._count_failed_logins(lines)

        brute_force = self._detect_brute_force(lines)

        shh_login = self._detect_shh_login(lines)

        new_systemd_service = self._detect_new_systemd_service(lines)

        log_tampering = self._detect_log_tampering(lines)

        features = {

            "count_failed_logins" : count_failed_logins,
            "brute_force" : brute_force,
            "shh_login" : shh_login,
            "new_systemd_service" : new_systemd_service,
            "log_tampering" : log_tampering,

            "total_lines" : lines,
            "log_path" : log_path,
            "parsed_at" : dt.utcnow().isoformat()

        }

        if to_redis:

            self._save_to_redis()

        return features


log_parser = LogsParser()
