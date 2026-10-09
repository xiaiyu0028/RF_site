import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def parse_args():
	parser = argparse.ArgumentParser(description="Run get_actors.py for all accounts")
	parser.add_argument(
		"--config",
		type=str,
		default=None,
		help="Path to config.json (default: repo root config.json)",
	)
	parser.add_argument(
		"--include-disabled",
		action="store_true",
		help="Include accounts with enable=false in config.json",
	)
	parser.add_argument(
		"--delay-seconds",
		type=float,
		default=10.0,
		help="Delay between accounts (default: 2 seconds)",
	)
	parser.add_argument(
		"--start-index",
		type=int,
		default=1,
		help="Start from 1-based index in the filtered list (default: 1)",
	)
	parser.add_argument(
		"--limit",
		type=int,
		default=None,
		help="Max number of accounts to run (default: no limit)",
	)
	parser.add_argument(
		"--append",
		action="store_true",
		help="保留 actors.jsonl 既有紀錄並附加（預設會先清空；--start-index > 1 時自動附加）",
	)
	return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
	script_dir = Path(__file__).resolve().parent
	repo_root = script_dir.parent

	config_path = Path(args.config) if args.config else repo_root / "config.json"
	get_actors_path = script_dir / "get_actors.py"

	return config_path, get_actors_path


def load_accounts(config_path: Path, include_disabled: bool) -> list[dict]:
	with config_path.open("r", encoding="utf-8") as f:
		data = json.load(f)

	if not isinstance(data, list):
		raise ValueError("config.json must be a list of account objects")

	accounts = []
	for item in data:
		if not isinstance(item, dict):
			continue
		if not include_disabled and not bool(item.get("enable", False)):
			continue
		account = item.get("account")
		password = item.get("password")
		if not account or not password:
			continue
		accounts.append(item)

	return accounts


def count_lines(path: Path) -> int:
	if not path.exists():
		return 0
	with path.open("r", encoding="utf-8") as f:
		return sum(1 for line in f if line.strip())


def run_get_actors(
	get_actors_path: Path,
	account: str,
	password: str,
	working_dir: Path,
) -> int:
	cmd = [sys.executable, str(get_actors_path), "--email", account, "--password", password]
	proc = subprocess.run(
		cmd,
		cwd=str(working_dir),
		text=True,
		check=False,
	)
	return proc.returncode


def main():
	args = parse_args()
	config_path, get_actors_path = resolve_paths(args)

	if not get_actors_path.exists():
		raise FileNotFoundError(f"get_actors.py not found at {get_actors_path}")
	if not config_path.exists():
		raise FileNotFoundError(f"config.json not found at {config_path}")

	accounts = load_accounts(config_path, include_disabled=args.include_disabled)
	if not accounts:
		print("No accounts found to run.")
		return

	start_index = max(args.start_index, 1)
	selected = accounts[start_index - 1 :]
	if args.limit is not None:
		selected = selected[: args.limit]

	# get_actors.py 會附加寫入目前目錄下的 actors.jsonl
	output_path = (Path.cwd() / "actors.jsonl").resolve()
	backup_path = output_path.with_name(output_path.name + ".bak")
	print(f"Total accounts to run: {len(selected)}")
	print(f"Output file: {output_path}")

	# 預設先清掉舊紀錄，避免新舊資料混在一起；從中途續跑（--start-index）時保留前面帳號的資料
	append = args.append or start_index > 1
	cleared = False
	if not append and output_path.exists():
		shutil.move(str(output_path), str(backup_path))
		cleared = True
		print(f"已清空舊紀錄（備份於 {backup_path.name}）")
	elif append:
		print("保留既有紀錄，以附加方式寫入")

	failures = []
	for idx, item in enumerate(selected, start=start_index):
		account = str(item.get("account"))
		password = str(item.get("password"))

		print(f"[{idx}] Running account={account}")
		before = count_lines(output_path)
		code = run_get_actors(get_actors_path, account, password, Path.cwd())
		# get_actors.py 連線失敗時仍會以 exit 0 結束，所以改看有沒有實際寫入資料
		if code != 0 or count_lines(output_path) <= before:
			failures.append((idx, account, code))
			print(f"[{idx}] Failed (exit={code}，沒有寫入角色資料).")
		else:
			print(f"[{idx}] Done.")

		if args.delay_seconds > 0:
			time.sleep(args.delay_seconds)

	if cleared and count_lines(output_path) == 0:
		shutil.move(str(backup_path), str(output_path))
		print("\n所有帳號都沒有抓到資料，已還原原本的 actors.jsonl。")
		sys.exit(1)

	if failures:
		print("\nFailed accounts:")
		for idx, account, code in failures:
			print(f"- [{idx}] {account} (exit={code})")
	else:
		print("\nAll accounts completed successfully.")


if __name__ == "__main__":
	main()
