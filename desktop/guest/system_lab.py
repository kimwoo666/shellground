"""Actual read-only system investigation and owned veth fixture; guest only."""
import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time

if __package__:
    from .auth_lab import guard, read
    from .shell_lab import signature
else:
    from auth_lab import guard, read
    from shell_lab import signature

OWNED = Path('/opt/shellground/system-owned.json')
KEYS = ('system_identity', 'system_links', 'system_addresses', 'system_time', 'system_clock', 'system_review')
STALE = b'Previous machine report: preserve before replacing.\n'
NOTES = b'Original operator notes. Preserve the contents and modification time.\n'
INCIDENT = b'Received claim: a kernel release is the distribution version; an address proves connectivity. Verify instead of trusting this claim.\n'
IDENTITY = dict(kernel=['uname', '-s'], release=['uname', '-r'], machine=['uname', '-m'], host=['hostname'], all=['uname', '-a'])
PROPERTIES = ('Timezone', 'LocalRTC', 'NTP', 'NTPSynchronized')


def run(*args, required=True):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=12,
                            env=dict(os.environ, LC_ALL='C', TZ='UTC'))
    if required and result.returncode: raise RuntimeError('System fixture query failed: ' + ' '.join(args) + '\n' + result.stderr.decode(errors='replace'))
    return result


def validate(m):
    seed = m['seed']; plan = m['review']
    if type(seed) is not int or not 0 <= seed <= 9999 or m['kind'] not in KEYS or type(m['practice']) is not int or m['practice'] not in (0, 1, 2):
        raise ValueError('Invalid system exercise')
    start = Path(f'/home/learner/system/session{seed}')
    if m['start'] != str(start) or plan['interfaces'] != [f'sgsi{seed}a', f'sgsi{seed}b']: raise ValueError('Invalid owned system paths')
    if set(plan['identity']) - set(IDENTITY) - {'os_release', 'distro'} or plan['time'] not in ('', 'now', 'event', 'mtime'):
        raise ValueError('Invalid system report type')
    if set(plan['links']) - {'links.txt', 'legacy.txt', 'spare-link.txt'} or set(plan['addresses']) - {'ipv4.txt', 'ipv6.txt', 'active-addresses.txt', 'spare-addresses.txt'}:
        raise ValueError('Invalid report target')
    for names in plan['links'].values():
        if names and (len(names) != 1 or names[0] not in plan['interfaces']): raise ValueError('Unknown interface')
    for spec in plan['addresses'].values():
        if spec['interface'] not in plan['interfaces'] or spec['families'] not in (['inet'], ['inet6'], ['inet', 'inet6']): raise ValueError('Unknown address selection')
    return start, plan


def network():
    rows = json.loads(run('ip', '-j', 'address', 'show').stdout)
    links = {row['ifname']: row for row in json.loads(run('ip', '-j', 'link', 'show').stdout)}
    return {row['ifname']: dict(up='UP' in row['flags'], mtu=row['mtu'], mac=row.get('address'),
                              index=links[row['ifname']]['ifindex'], alias=links[row['ifname']].get('ifalias'),
                              addresses=sorted([a['family'], a['local'] + '/' + str(a['prefixlen'])] for a in row.get('addr_info', []))) for row in rows}


def interface_identity(name):
    result = run('ip', '-j', 'link', 'show', 'dev', name, required=False)
    if result.returncode: return None
    row = json.loads(result.stdout)[0]
    return {'index': row['ifindex'], 'alias': row.get('ifalias')}


def cleanup():
    guard()
    if not OWNED.exists(): return {'clean': True}
    info = json.loads(OWNED.read_text())
    for name, identity in info.items():
        if not re.fullmatch(r'sgsi[0-9]{1,4}[ab]', name) or not str(identity.get('alias', '')).startswith('shellground-system-'):
            raise RuntimeError('Refuse unrelated interface cleanup')
        current = interface_identity(name)
        if current is not None:
            if current != identity: raise RuntimeError('Owned interface identity changed; refusing ambiguous cleanup')
            run('ip', 'link', 'delete', 'dev', name)
    OWNED.unlink()
    return {'clean': True}


def clock_properties():
    args = ['timedatectl', 'show']
    for name in PROPERTIES: args += ['-p', name]
    return parse_properties(run(*args).stdout)


def system_files():
    result = {}
    for name in ('/etc/hostname', '/etc/hosts', '/etc/localtime', '/etc/timezone', '/etc/adjtime', '/etc/os-release'):
        path = Path(name)
        if path.is_symlink(): result[name] = ['link', os.readlink(path), signature(path.resolve())]
        else: result[name] = signature(path)
    return result


def prepare(m):
    guard(); start, plan = validate(m)
    start.mkdir(parents=True, exist_ok=True); (start / 'reports').mkdir(exist_ok=True)
    stamp = 1700000000 + m['seed'] * 60
    event = datetime.datetime.fromtimestamp(stamp, datetime.timezone(datetime.timedelta(hours=9))).isoformat()
    for name, content in {'personal.txt': NOTES, 'source notes.txt': NOTES, 'received notes.txt': INCIDENT,
                          'event time.txt': (event + '\n').encode()}.items():
        path = start / name; path.write_bytes(content); os.utime(path, (stamp, stamp))
    if plan['backup']: (start / 'all.txt').write_bytes(STALE)
    for path in (start, *start.rglob('*')): os.chown(path, 1100, 1100)
    if plan['links'] or plan['addresses']:
        cleanup(); active, spare = plan['interfaces']
        if any(interface_identity(name) is not None for name in (active, spare)): raise RuntimeError('Reserved interface name is already in use')
        run('ip', 'link', 'add', active, 'type', 'veth', 'peer', 'name', spare)
        for name in (active, spare):
            run('ip', 'link', 'set', 'dev', name, 'alias', f'shellground-system-{m["seed"]}-v1')
            # Keep the teaching addresses stable when learners restore link state.
            run('ip', 'link', 'set', 'dev', name, 'addrgenmode', 'none')
        OWNED.write_text(json.dumps({name: interface_identity(name) for name in (active, spare)})); OWNED.chmod(0o600)
        run('ip', 'address', 'add', f'192.0.2.{10 + m["seed"] % 100}/24', 'dev', active)
        run('ip', '-6', 'address', 'add', f'2001:db8:{m["seed"]:x}::1/64', 'nodad', 'dev', active)
        run('ip', 'address', 'add', f'198.51.100.{17 + m["seed"] % 10}/28', 'dev', spare)
        run('ip', 'link', 'set', 'dev', active, 'up')
    identity = {name: run(*args).stdout.decode() for name, args in IDENTITY.items()}
    identity['os_release'] = Path('/etc/os-release').read_text()
    identity['distro'] = '\n'.join(line for line in identity['os_release'].splitlines() if line.startswith('VERSION_ID=')) + '\n'
    reference = dict(identity=identity, network=network(), clock=clock_properties(), files=system_files(),
                     start_epoch=time.time(), start_monotonic=time.monotonic(), event_epoch=stamp,
                     originals={name: [signature(start / name), (start / name).stat().st_mtime_ns] for name in
                                ('personal.txt', 'source notes.txt', 'received notes.txt', 'event time.txt')})
    return {'ready': True, 'reference': reference}


def parse_properties(data):
    if data is None: return None
    result = {}
    for line in data.decode(errors='replace').splitlines():
        name, sep, value = line.partition('=')
        if not sep or name in result: return None
        result[name] = value
    return result


def clean_name(name): return name.split('@', 1)[0].rstrip(':')


def parse_links(data, legacy=None):
    if data is None: return None
    text = data.decode(errors='replace'); result = {}
    for line in text.splitlines():
        if legacy is True:
            match = re.match(r'^(\S+): flags=\d+<([^>]*)>', line)
        else:
            match = re.match(r'^\d+: (\S+): <([^>]*)>', line) or re.match(r'^(\S+)\s+\S+\s+\S+\s+<([^>]*)>', line)
            if legacy is None and not match:
                match = re.match(r'^(\S+): flags=\d+<([^>]*)>', line)
        if match:
            name = clean_name(match[1])
            if name in result: return None
            result[name] = 'UP' in match[2].split(',')
    return result or None


def parse_addresses(data):
    if data is None: return None
    result = {}; current = None
    for line in data.decode(errors='replace').splitlines():
        header = re.match(r'^\d+: (\S+?)(?:: |\s+inet)', line)
        brief = re.match(r'^(\S+)\s+(?:UP|DOWN|UNKNOWN|LOWERLAYERDOWN|DORMANT)\s*(.*)', line)
        if header or brief:
            current = clean_name((header or brief)[1])
            result.setdefault(current, [])
        if current is None:
            if line.strip(): return None
            continue
        candidates = re.findall(r'\binet6?\s+(\S+/\d+)', line)
        if brief: candidates = re.findall(r'\S+/\d+', brief[2])
        for candidate in candidates:
            try:
                address = ipaddress.ip_interface(candidate)
                pair = ['inet' if address.version == 4 else 'inet6', str(address)]
            except ValueError: return None
            if pair in result[current]: return None
            result[current].append(pair)
    return {name: sorted(values) for name, values in result.items()} if result else None


def integer(path):
    value = read(path)
    if value is None or not re.fullmatch(rb'-?\d+\n?', value): return None
    return int(value)


def utc(stamp):
    try: return datetime.datetime.fromtimestamp(stamp, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ').encode() + b'\n'
    except (ValueError, OverflowError, OSError, TypeError): return None


def clock_settings(properties):
    # Synchronization is an observation, not a configuration setting.
    return {key: properties[key] for key in PROPERTIES if key != 'NTPSynchronized'}


def clock_report_matches(recorded, initial, current):
    return (recorded is not None and set(recorded) == set(PROPERTIES) and
            clock_settings(recorded) == clock_settings(current) and
            recorded['NTPSynchronized'] in {'yes', 'no'} & {initial['NTPSynchronized'], current['NTPSynchronized']})


def rtc_report_matches(output, code, observed, elapsed):
    if observed.returncode:
        return code == observed.returncode and output == observed.stdout + observed.stderr
    try:
        lines = output.decode().splitlines()
        if len(lines) != 1: return False
        stamp = datetime.datetime.fromisoformat(lines[0]).timestamp()
        measured = datetime.datetime.fromisoformat(observed.stdout.decode().splitlines()[0]).timestamp()
        # Compare the RTC to itself over elapsed monotonic time, not to the system clock.
        return code == 0 and measured - max(0, elapsed) - 5 <= stamp <= measured + 5
    except (AttributeError, ValueError, IndexError): return False


def grade(m):
    guard(); start, plan = validate(m); ref = m['_reference']; checks = []
    def check(label, value): checks.append(dict(label=label, passed=bool(value)))
    if plan['identity']:
        ok = all(read(start / (name + '.txt')) == ref['identity'][name].encode() for name in plan['identity'])
        if plan['backup']: ok = ok and read(start / 'previous report.txt') == STALE
        check('커널·배포판·이름 구분 및 요구한 이전 보고 보존', ok)
    if plan['links']:
        ok = True
        for name, targets in plan['links'].items():
            expected = {key: value['up'] for key, value in ref['network'].items() if not targets or key in targets}
            required_format = (name == 'legacy.txt') if m['kind'] == 'system_links' and m['practice'] == 1 else None
            ok = ok and parse_links(read(start / name), legacy=required_format) == expected
        if m['kind'] == 'system_links' and m['practice'] == 2:
            ok = ok and read(start / 'state.txt') == ('UP\n' if ref['network'][plan['interfaces'][1]]['up'] else 'DOWN\n').encode()
        check('인터페이스 조회 범위·관리 상태와 내려간 항목', ok)
    if plan['addresses']:
        ok = True
        for name, spec in plan['addresses'].items():
            expected = {spec['interface']: [list(a) for a in ref['network'][spec['interface']]['addresses'] if a[0] in spec['families']]}
            ok = ok and parse_addresses(read(start / name)) == expected
        if plan['incident_copy']: ok = ok and read(start / 'reports/received notes.txt') == INCIDENT
        check('인터페이스·주소 종류·접두 길이 및 원본 인계', ok)
    if plan['time']:
        current = integer(start / 'epoch.txt'); mode = plan['time']
        now_ok = current is not None and ref['start_epoch'] - 2 <= current <= time.time() + 2
        if mode == 'now': ok = now_ok and read(start / 'utc.txt') == utc(current)
        elif mode == 'event':
            ok = integer(start / 'event-epoch.txt') == ref['event_epoch'] and read(start / 'event-utc.txt') == utc(ref['event_epoch'])
        else:
            stamp = ref['originals']['source notes.txt'][1] // 1_000_000_000
            ok = now_ok and integer(start / 'modified-epoch.txt') == stamp and read(start / 'modified-utc.txt') == utc(stamp)
        check('요청한 현재·예정·수정 시각과 같은 순간의 UTC', ok)
    if plan['clock']:
        current_clock = clock_properties()
        recorded_clock = parse_properties(read(start / 'clock-state.txt'))
        ok = clock_report_matches(recorded_clock, ref['clock'], current_clock)
        if plan['rtc']:
            observed = run('/sbin/hwclock', '--show', required=False); code = integer(start / 'rtc-exit.txt'); output = read(start / 'rtc.txt')
            rtc_ok = rtc_report_matches(output, code, observed, time.monotonic() - ref['start_monotonic'])
            ok = ok and rtc_ok
            if plan['verdict']:
                expected = f'rtc={"available" if observed.returncode == 0 else "unavailable"}\nsynchronized={(recorded_clock or {}).get("NTPSynchronized")}\n'
                ok = ok and read(start / 'conclusion.txt') == expected.encode()
        check('시계 속성·실제 RTC 조회 결과와 성공 범위 구분', ok)
    originals = all(signature(start / name) == value[0] and (start / name).stat().st_mtime_ns == value[1] for name, value in ref['originals'].items())
    elapsed_clock = time.time() - ref['start_epoch']; elapsed_mono = time.monotonic() - ref['start_monotonic']
    check('원본 파일·이름·네트워크·시간 설정 보존', originals and system_files() == ref['files'] and
          network() == ref['network'] and run('hostname').stdout.decode() == ref['identity']['host'] and
          clock_settings(clock_properties()) == clock_settings(ref['clock']) and
          (ref['clock']['NTP'] == 'yes' or abs(elapsed_clock - elapsed_mono) < 5))
    return dict(passed=all(row['passed'] for row in checks), checks=checks)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'cleanup': result = cleanup()
    elif action in ('prepare', 'grade'): result = globals()[action](json.load(sys.stdin))
    else: raise SystemExit('Unknown system helper action')
    print(json.dumps(result))
