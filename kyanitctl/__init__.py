# Kyanit CTL
# Copyright (C) 2020 Zsolt Nagy
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software Foundation,
# version 3 of the License.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with this
# program. If not, see <https://www.gnu.org/licenses/>.

"""
# Kyanit CTL

Kyanit CTL is a command-line utility for interfacing and interacting with Kyanit.

For a Python API, see Kyanit API at
https://kyanit-project.github.io/kyanit-api/kyanitapi/.

Install the latest released version of Kyanit CTL from PyPI with:

```
pip install kyanitctl
```

After installation, Kyanit CTL will be available through the `kyanitctl` command.

# Usage

Refer to the command-line help with `kyanitctl -h`.

# License Notice

Copyright (C) 2020 Zsolt Nagy

This program is free software: you can redistribute it and/or modify it under the terms
of the GNU General Public License as published by the Free Software Foundation, version
3 of the License.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.
See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this
program. If not, see <https://www.gnu.org/licenses/>.
"""


import os
import json
import time
import pathlib
import argparse
import collections

from kyanitapi import Kyanit
from kyanitapi import KyanitRequestError
from kyanitapi import KyanitConnectionError
from kyanitapi import ip_is_valid
from kyanitapi import get_networks
from kyanitapi import netmask_is_valid

try:
    from ._version import __version__  # noqa
except ImportError:
    pass


__pdoc__ = {}

KYANITCTL_USER_DIR = os.path.join(pathlib.Path.home(), ".kyanitctl")

if not os.path.exists(KYANITCTL_USER_DIR):
    os.mkdir(KYANITCTL_USER_DIR)

EXAMPLE_CODE = """
# This code is imported on startup, then main is called, if it exists. Neither main, nor
# cleanup should block for too long.
# Use coroutines through kyanit.runner.create_task('name', coro) for continuous or
# longer tasks. Any errors (including from coroutines) will be passed to cleanup.
# The @kyanit.controls() decorator adds functionality to the LEDs and button. It can be
# removed if this is not required, to save approximately 1k of RAM.

# To get started, head to https://kyanit.eu

import kyanit

@kyanit.controls()
def main():
    pass


@kyanit.controls()
def cleanup(exception):
    pass
"""


def input_validate(msg, validator):
    inp = ""
    while not validator(inp):
        print("{}: ".format(msg), end="")
        inp = input()
        if not validator(inp):
            print("Invalid, try again...")
    return inp


__pdoc__["input_validate"] = False


def get_saved_network():
    try:
        network = json.load(open(os.path.join(KYANITCTL_USER_DIR, "network.json")))
        return (network["interface"], network["ip_address"])
    except (FileNotFoundError, KeyError):
        return None


__pdoc__["get_saved_network"] = False


def save_network(network):
    try:
        if len(network) != 2:
            raise TypeError("network must be indexable with 2 items")
    except TypeError:
        raise TypeError("network must be indexable with 2 items")
    json.dump(
        {"interface": network[0], "ip_address": network[1]},
        open(os.path.join(KYANITCTL_USER_DIR, "network.json"), "w"),
    )


__pdoc__["save_network"] = False


def _action_handler(extra_msg=""):
    def decorated(func):
        def handle_action(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except (KyanitConnectionError, OSError):
                print("\nERROR: Cannot connect to Kyanit.", end="\n\n")
                if extra_msg:
                    print(extra_msg)
                exit()
            except KyanitRequestError as exc:
                print(
                    "\nERROR: Kyanit responded with status code {}".format(exc.args[0]),
                    end="\n\n",
                )

        return handle_action

    return decorated


class VerboseAction:
    def __init__(self, kyanit: Kyanit):
        if not isinstance(kyanit, Kyanit):
            raise ValueError("must provide instance of Kyanit")
        self.kyanit: Kyanit = kyanit

    @_action_handler("MAKE SURE YOU'RE CONNECTED TO KYANIT'S WLAN!")
    def setup(self, static=False):
        print("=== Kyanit WLAN Setup Procedure ===", end="\n\n")
        status = self.kyanit.get_status()
        print(
            "Connection established. Firmware version is {}.".format(
                status["firmware_version"]
            )
        )
        print("Network name (SSID): ", end="")
        ssid = input()
        print("Password (blank if Open): ", end="")
        password = input()
        if not static:
            ifconfig = "dhcp"
        else:
            ip_addr = input_validate("IP Address", ip_is_valid)
            netmask = input_validate("Netmask", netmask_is_valid)
            gateway = input_validate("Gateway", ip_is_valid)
            dns = input_validate("DNS", ip_is_valid)
            ifconfig = (ip_addr, netmask, gateway, dns)
        config = {"ssid": ssid, "password": password, "ifconfig": ifconfig}
        print("\nConfiguration (wlan.json) will be:", end="\n\n")
        print(json.dumps(config, indent=2, sort_keys=True), end="\n\n")
        print("Ready to upload to Kyanit? (YES/no) ", end="")
        try:
            upload = input()
            upload = True if not upload or upload.upper() == "YES" else False
            if not upload:
                print("Aborted.", end="\n\n")
                return
            print("\nUploading...")
            self.kyanit.put_file("wlan.json", json.dumps(config))
            print("Uploading blank code.py (if non-existent)...")
            if "code.py" not in self.kyanit.get_file_list():
                self.kyanit.put_file("code.py", EXAMPLE_CODE)
            print("Rebooting...")
            self.kyanit.reboot()
            print("Done.", end="\n\n")
        except KeyboardInterrupt:
            print("Aborted.", end="\n\n")

    @_action_handler("CHECK THE COLOR ID OR THE IP ADDRESS AGAIN!")
    def ping(self):
        print("Pinging...")
        success = self.kyanit.ping(verbose=True)
        print()
        if success:
            print("Retrieving system status...", end="\r")
            self.kyanit.get_status()
            print("Retrieving system status done.")
            conn_info = self.kyanit.info()
            print(
                "Kyanit {} is responding on IP address {}.".format(
                    conn_info["color_id"], conn_info["ip_addr"]
                )
            )
        else:
            raise KyanitConnectionError
        print()

    @_action_handler()
    def print_status_info(self, tries=1):
        print("Retrieving system status...")
        status = collections.OrderedDict(sorted(self.kyanit.get_status(tries).items()))
        print()
        for key in status:
            if key != "error_traceback" and key != "color_id":
                print(
                    "{:>20}: {}".format(key.replace("_", " ").capitalize(), status[key])
                )
            elif key == "error_traceback":
                if status["error_traceback"]:
                    print(
                        "{:>20}: {}".format(
                            "Error detail", "Traceback (most recent call last):"
                        )
                    )
                    for line in status["error_traceback"]:
                        print("{:>20}  {}".format("", line))
        print()

    @_action_handler()
    def stop(self, force=False):
        print("Stopping code.py{}...".format(" (forcibly)" if force else ""), end="\r")
        self.kyanit.stop(force)
        print("Stopping code.py{} done.".format(" (forcibly)" if force else ""))
        print()

    @_action_handler()
    def start(self):
        print("Starting code.py...", end="\r")
        self.kyanit.start()
        print("Starting code.py done.")
        print()

    @_action_handler()
    def reboot(self, tries=5):
        print("Rebooting (hard reset) ...", end="\r")
        self.kyanit.reboot()
        # wait until reboot is asserted
        time.sleep(1.5)
        # wait until Kyanit comes back
        self.kyanit.get_status(tries)
        print("Rebooting (hard reset) done.")
        print()

    # @_action_handler()
    # def reset(self, tries=5):
    #     print('Rebooting (soft reset) ...', end='\r')
    #     self.kyanit.reset()
    #     # wait until reboot is asserted
    #     time.sleep(1.5)
    #     # wait until Kyanit comes back
    #     self.kyanit.get_status(tries)
    #     print('Rebooting (soft reset) done.')
    #     print()

    @_action_handler()
    def print_file_list(self):
        print("Retrieving file list...", end="\r")
        files = self.kyanit.get_file_list()
        print("Retrieving file list done.")
        print("Files on Kyanit:", end="\n\n")
        for file in files:
            print(file)
        print()

    @_action_handler()
    def get_files(self, filenames=[], all_files=False):
        if all_files:
            print("Downloading all files...")
            for filename in self.kyanit.get_file_list():
                print("Downloading '{}' ...".format(filename), end="\r")
                with open(filename, "wb") as file:
                    file.write(self.kyanit.get_file(filename))
                    print("Downloading '{}' done.".format(filename))
            print("Done.", end="\n\n")
            return

        for filename in filenames:
            try:
                print("Downloading '{}' ...".format(filename), end="\r")
                data = self.kyanit.get_file(filename)
                with open(filename, "wb") as file:
                    file.write(data)
                print("Downloading '{}' done.".format(filename))
            except KyanitRequestError as exc:
                if exc.args[0] == 404:
                    print("Downloading '{}' (not found, skipping)".format(filename))
                else:
                    print("Downloading '{}' (error {})".format(filename, exc.args[0]))
        print("Done.", end="\n\n")

    @_action_handler()
    def print_file(self, filename):
        try:
            print("Downloading '{}' ...".format(filename), end="\r")
            data = self.kyanit.get_file(filename)
            print("Downloading '{}' done.".format(filename))
            print("Contents:", end="\n\n")
            try:
                print(data.decode())
            except Exception:
                print(data)
        except KyanitRequestError as exc:
            if exc.args[0] == 404:
                print()
                print("File '{}' not found on Kyanit.".format(filename))
            else:
                raise
        print()

    @_action_handler()
    def put_files(self, pathnames):
        for path in pathnames:
            if os.path.isdir(path):
                for name in os.listdir(path):
                    if not os.path.isdir(os.path.join(path, name)):
                        print(
                            "Uploading '{}' ...".format(os.path.join(path, name)),
                            end="\r",
                        )
                        with open(os.path.join(path, name), "rb") as file:
                            self.kyanit.put_file(os.path.basename(name), file)
                        print("Uploading '{}' done.".format(os.path.join(path, name)))
            else:
                print("Uploading '{}' ...".format(path), end="\r")
                if not os.path.exists(path):
                    print("Uploading '{}' (not found, skipping)".format(path))
                    continue
                with open(os.path.basename(path), "rb") as file:
                    self.kyanit.put_file(os.path.basename(path), file)
                print("Uploading '{}' done.".format(path))
        print("Done.", end="\n\n")

    @_action_handler()
    def delete_files(self, filenames=[], purge=False):
        if purge:
            print("Deleting all files on Kyanit (except wlan.json)!")
            file_list = self.kyanit.get_file_list()
            for filename in file_list:
                if filename != "wlan.json":
                    print("Deleting '{}' ...".format(filename), end="\r")
                    self.kyanit.delete_file(filename)
                    print("Deleting '{}' done.".format(filename))
            print("Done.", end="\n\n")
            return
        for filename in filenames:
            try:
                print("Deleting '{}' ...".format(filename), end="\r")
                self.kyanit.delete_file(filename)
                print("Deleting '{}' done.".format(filename))
            except KyanitRequestError as exc:
                if exc.args[0] == 404:
                    print("Deleting '{}' (not found, skipping)".format(filename))
                else:
                    raise
        print("Done.", end="\n\n")

    @_action_handler()
    def rename_file(self, filename, newname):
        try:
            print("Renaming '{}' to '{}' ...".format(filename, newname), end="\r")
            self.kyanit.rename_file(filename, newname)
            print("Renaming '{}' to '{}' done.".format(filename, newname))
        except KyanitRequestError as exc:
            if exc.args[0] == 404:
                print("File '{}' not found on Kyanit.".format(filename))
            else:
                raise
        print()

    @_action_handler()
    def netvar(self, json_str=None):
        if json_str is None:
            print("Getting outbound netvar...", end="\r")
            netvar = self.kyanit.netvar()
            print("Getting outbound netvar done.")
            if netvar is None:
                print("Netvar empty.")
            else:
                netvar_json = json.dumps(self.kyanit.netvar(), indent=2, sort_keys=True)
                print("Netvar is:", end="\n\n")
                print(netvar_json)
            print()
            return

        try:
            obj = json.loads(json_str)
        except json.decoder.JSONDecodeError:
            print("ERROR: Malformed JSON.")
        else:
            print("Setting inbound netvar to '{}' ...".format(json_str), end="\r")
            self.kyanit.netvar(obj)
            print("Setting inbound netvar to '{}' done.".format(json_str))
        print()


__pdoc__["VerboseAction"] = False


def main(*cli_args):
    parser = argparse.ArgumentParser(
        prog="kyanitctl",
        description="Console application for managing a Kyanit board. If more than one"
        "option is provided, they are executed in the order they appear in the help.",
        usage="%(prog)s [-setup] [ColorID] [-ip IP] [options...]",
    )
    parser.add_argument(
        "colorid",
        nargs="?",
        help="primary connection method; color identifier of the Kyanit, "
        "which is a set of 3 letters representing colors Red, Green, Blue, "
        "Cyan, Magenta, Yellow or White; after initial setup, these colors "
        "show up on the Kyanit, when the button is pressed; example: RGB, BGY "
        " etc.; must be omitted if -ip is given",
    )
    parser.add_argument(
        "-setup",
        action="store_true",
        help="initial setup of Kyanit; perform when first connected to the "
        "Kyanit's WLAN; must be on Kyanit's WLAN for setup to work; "
        "no other actions will be performed; Color ID and -ip don't have to "
        "be provided, and are disregarded",
    )
    parser.add_argument(
        "-setupstatic",
        action="store_true",
        help="same as setup, but this will configure the Kyanit with a static IP "
        "instead of DHCP; only recommended if you know what you're doing; "
        "misconfigured static IP will render your Kyanit inaccessible, and a "
        "rescue will be required",
    )
    parser.add_argument(
        "-ip",
        nargs="?",
        help="alternative connection method; IP address of the Kyanit, "
        "must be given if Color ID is omitted, or if Kyanit is on a non-/24 "
        "network",
    )
    parser.add_argument(
        "-reset_network",
        action="store_true",
        help="perform initial network selection again",
    )
    parser.add_argument(
        "-ping", action="store_true", help="ping the Kyanit and get system state"
    )
    parser.add_argument(
        "-timeout",
        metavar="SECONDS",
        type=int,
        help="set timeout for network operations, except ping; default is 5 " "seconds",
    )
    parser.add_argument(
        "-files", action="store_true", help="list files currently on Kyanit"
    )
    parser.add_argument(
        "-get",
        action="extend",
        nargs="+",
        metavar="FILE",
        help="a list of files to get from the Kyanit; warning, all existing local "
        "files will be irreversibly OVERWRITTEN!",
    )
    parser.add_argument(
        "-getall", action="store_true", help="same as -get, but it gets all files"
    )
    parser.add_argument(
        "-print", metavar="FILE", help="print contents of a file on Kyanit"
    )
    parser.add_argument(
        "-delete",
        action="extend",
        nargs="+",
        metavar="FILE",
        help="a list of files to delete on the Kyanit; WARNING: deleting wlan.json"
        " will require performing the initial setup again",
    )
    parser.add_argument(
        "-purge",
        action="store_true",
        help="same as -delete, but deletes all files; wlan.json is preserved",
    )
    parser.add_argument(
        "-put",
        action="extend",
        nargs="+",
        metavar="FILE",
        help="a list of files and directories to upload on the Kyanit; only "
        "top-level files will be uploaded from directories; existing remote "
        "files will be irreversibly OVERWRITTEN!",
    )
    parser.add_argument(
        "-rename",
        action="extend",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="renames a file on Kyanit",
    )
    parser.add_argument(
        "-netvar",
        nargs="?",
        action="append",
        metavar="JSON",
        help="get the outbound netvar if JSON is not specified,  or set the "
        "inbound netvar to JSON; valid JSON must be specified; escape double "
        'quotes with \\", use enclosing single quotes in Windows PowerShell, ex. '
        '-netvar \'{\\"some_string\\": \\"my_string\\"}\'',
    )
    parser.add_argument("-stop", action="store_true", help="start code.py")
    parser.add_argument(
        "-stopforce", action="store_true", help="forcibly stop code.py (no cleanup)"
    )
    parser.add_argument("-start", action="store_true", help="stop running code.py")
    parser.add_argument(
        "-reboot", action="store_true", help="reboot Kyanit (hard reset)"
    )
    # parser.add_argument('-reset', action='store_true',
    #                     help='reset Kyanit (soft reset)')
    parser.add_argument("-status", action="store_true", help="get status info")

    args = parser.parse_args(*cli_args)
    print()

    # SETUP

    if args.setup or args.setupstatic:
        kyanit = Kyanit(ip_addr="192.168.4.1")
        action = VerboseAction(kyanit)
        action.setup(static=args.setupstatic)
        exit()

    # BBB COLORID

    if args.colorid == "BBB":
        print("A Color ID of BBB means the Kyanit lost connection to WiFi.")
        print(
            "This may have happened, because your WiFi SSID or password has changed. "
            "In that case, power-cycle your Kyanit, connect to it, and re-run "
            "kyanitctl -setup."
        )
        print()
        exit()

    # SELECT NETWORK

    network = get_saved_network()
    if (network is None and args.colorid is not None) or args.reset_network:

        def select(networks):
            for network in enumerate(networks):
                print(
                    "{}:".format(network[0]),
                    "{:<15}".format(network[1][1]),
                    network[1][0],
                )
            print()
            while True:
                print("Select network {}: ".format(list(range(len(network)))), end="")
                index = input()
                try:
                    return networks[int(index)]
                except (IndexError, TypeError, ValueError):
                    print("Invalid selection.")

        print("=== Network Setup ===", end="\n\n")
        print(
            "Connecting to Kyanit with the Color ID works on networks with a netmask "
            "of 255.255.255.0 (most home wireless networks)."
        )
        networks = get_networks()
        if len(networks) == 0:
            if not args.ip:
                print(
                    "No such network detected. "
                    "Connection with Color ID is not supported. "
                    "Specify -ip instead. See kyanit -h for details."
                )
                exit()
        if len(networks) == 1:
            network = networks.pop()
            print(
                "Detecting one such network '{}' with IP {}.".format(
                    network[0], network[1]
                )
            )
            print(
                "If Kyanit is not on this network, "
                "connect with -ip instead of the Color ID."
            )
        if len(networks) > 1:
            print(
                "Multiple such networks detected. "
                "Select the one Kyanit is connected to:"
            )
            network = select(networks)
        if network is not None:
            save_network(network)
            print("Saved. You may re-run this setup with -reset_network.", end="\n\n")
        if args.reset_network:
            exit()

    # OPEN KYANIT

    try:
        kyanit = Kyanit(
            args.colorid, network[1] if network is not None else None, args.ip
        )
        kyanit.set_timeout(5)
    except ValueError as exc:
        if str(exc) == "IP invalid":
            parser.print_usage()
            print()
            print("The IP address '{}' is invalid.".format(args.ip))
            print("See kyanitctl -h for help.", end="\n\n")
            exit()
        elif str(exc) == "Color ID invalid":
            parser.print_usage()
            print()
            print(
                "The Color ID '{}' is invalid. "
                "It either contains unsupported characters, or "
                "the resulting IP address octet would be greater than 254.".format(
                    args.colorid
                )
            )
            print("See kyanitctl -h for help.", end="\n\n")
            exit()
        elif str(exc) == "Network invalid":
            # kyanitapi error when invalid network address is passed to Kyanit()
            # this should not normally happen with kyanitctl, as network addresses are
            # detected automatically.
            print("ERROR: Unexpected error (network address invalid).")
            print("Try re-running kyanitctl -reset_network.", end="\n\n")
            exit()
        elif str(exc) == "no connection method":
            parser.print_usage()
            print()
            print("No connection method. Either Color ID or -ip must be provided.")
            print("See kyanitctl -h for help.", end="\n\n")
            exit()
        elif str(exc) == "bad connection method":
            parser.print_usage()
            print()
            print(
                "Bad connection method. Either Color ID or -ip must be provided, "
                "but not both.",
                end="\n\n",
            )
            print("See kyanitctl -h for help.", end="\n\n")
            exit()
        else:
            raise exc

    if args.timeout:
        kyanit.set_timeout(args.timeout)

    if args.ip is None:
        print(
            "=== Kyanit {} ({} through '{}') ===".format(
                kyanit.info()["color_id"], kyanit.info()["ip_addr"], network[0]
            )
        )
    else:
        print("=== Kyanit on {} ===".format(kyanit.info()["ip_addr"]))
    print()

    action = VerboseAction(kyanit)

    # ACTIONS

    if args.ping:
        action.ping()

    if args.files:
        action.print_file_list()

    if args.get or args.getall:
        if args.getall:
            action.get_files(all_files=True)
        else:
            action.get_files(args.get)

    if args.print:
        action.print_file(args.print)

    if args.delete or args.purge:
        if args.purge:
            action.delete_files(purge=True)
        else:
            action.delete_files(args.delete)

    if args.put:
        action.put_files(args.put)

    if args.rename:
        action.rename_file(args.rename[0], args.rename[1])

    if args.netvar:
        if args.netvar[0] is None:
            action.netvar()
        else:
            action.netvar(args.netvar[0])

    if args.stop or args.stopforce:
        action.stop(force=args.stopforce)

    if args.start:
        action.start()

    if args.reboot:
        action.reboot()

    # if args.reset:
    #     action.reset()

    if args.status:
        action.print_status_info()


__pdoc__["main"] = False


def command_line(*args):
    try:
        main(*args)
    except KeyboardInterrupt:
        print("Aborted.", end="\n\n")


__pdoc__["command_line"] = False
