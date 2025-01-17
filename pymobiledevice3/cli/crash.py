import click

from pymobiledevice3.cli.cli_common import Command
from pymobiledevice3.lockdown import LockdownClient
from pymobiledevice3.services.afc import AfcShell
from pymobiledevice3.services.crash_reports import CrashReports


@click.group()
def cli():
    """ crash cli """
    pass


@cli.group()
def crash():
    """ crash report options """
    pass


@crash.command('clear', cls=Command)
def crash_clear(lockdown: LockdownClient):
    """ clear(/remove) all crash reports """
    CrashReports(lockdown).clear()


@crash.command('pull', cls=Command)
@click.argument('out', type=click.Path(file_okay=False))
@click.argument('remote_file', type=click.Path(), required=False)
@click.option('-e', '--erase', is_flag=True)
def crash_pull(lockdown: LockdownClient, out, remote_file, erase):
    """ pull all crash reports """
    if remote_file is None:
        remote_file = '/'
    CrashReports(lockdown).pull(out, remote_file, erase)


@crash.command('shell', cls=Command)
def crash_shell(lockdown: LockdownClient):
    """ start an afc shell """
    AfcShell(lockdown=lockdown, service_name=CrashReports.COPY_MOBILE_NAME).cmdloop()


@crash.command('ls', cls=Command)
@click.argument('remote_file', type=click.Path(), required=False)
@click.option('-d', '--depth', type=click.INT, default=1)
def crash_ls(lockdown: LockdownClient, remote_file, depth):
    """ List  """
    if remote_file is None:
        remote_file = '/'
    for path in CrashReports(lockdown).ls(remote_file, depth):
        print(path)


@crash.command('flush', cls=Command)
def crash_mover_flush(lockdown: LockdownClient):
    """ trigger com.apple.crashreportmover to flush all products into CrashReports directory """
    CrashReports(lockdown).flush()


@crash.command('watch', cls=Command)
@click.argument('name', required=False)
@click.option('-r', '--raw', is_flag=True)
def crash_mover_watch(lockdown: LockdownClient, name, raw):
    """ watch for crash report generation """
    for crash_report in CrashReports(lockdown).watch(name=name, raw=raw):
        print(crash_report)
