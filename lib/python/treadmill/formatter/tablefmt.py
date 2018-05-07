"""Table CLI formatter.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import time

import prettytable
import six

from treadmill import yamlwrapper as yaml


def fmt_time(timestamp):
    """Return ISO formatted time from seconds from epoch."""
    if timestamp:
        return time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(timestamp))
    else:
        return '-'


def fmt_utilization(util):
    """Format utilization."""
    return '{0:.4f}'.format(util)


def wrap_words(words, length, sep=',', newline='\n'):
    """Join words by sep, no more than count in each line."""
    lines = []
    line = []
    cur_length = 0
    while True:
        if not words:
            lines.append(line)
            break

        if cur_length + len(line) > length:
            lines.append(line)
            cur_length = 0
            line = []

        word = words.pop(0)
        cur_length += len(word)
        line.append(word)

    return newline.join([sep.join(line) for line in lines])


def make_wrap_words(length, sep=','):
    """Returng wrap words function."""
    return lambda words: wrap_words(words, length, sep)


def _make_table(columns, header=False, align=None):
    """Make a table object for output."""
    if not align:
        align = {}

    table = prettytable.PrettyTable(columns)
    for col in columns:
        table.align[col] = align.get(col, 'l')

    table.set_style(prettytable.PLAIN_COLUMNS)
    # For some reason, headers must be disable after set_style.
    table.header = header

    table.left_padding_width = 0
    table.right_padding_width = 2
    return table


def _cell(item, column, key, fmt):
    """Constructs a value in table cell."""
    if key is None:
        key = column

    if isinstance(key, six.string_types):
        keys = [key]
    else:
        keys = key

    raw_value = None
    for k in keys:
        if k in item and item[k] is not None:
            raw_value = item[k]
            break

    if callable(fmt):
        try:
            value = fmt(raw_value)
        except Exception:  # pylint: disable=W0703
            if raw_value is None:
                value = '-'
            else:
                raise
    else:
        if raw_value is None:
            value = '-'
        else:
            if isinstance(raw_value, list):
                value = ','.join(six.moves.map(str, raw_value))
            else:
                value = raw_value
    return value


def dict_to_table(item, schema):
    """Display object as table."""
    table = _make_table(['key', '', 'value'], header=False)
    for column, key, fmt in schema:
        value = _cell(item, column, key, fmt)
        table.add_row([column, ':', value])

    return table


def make_dict_to_table(schema):
    """Return dict to table function given schema."""
    return lambda item: dict_to_table(item, schema)


def list_to_table(items, schema, header=True, align=None):
    """Display  list of items as table."""
    columns = [column for column, _, _ in schema]
    table = _make_table(columns, header=header, align=align)
    if items is None:
        items = []
    for item in items:
        row = []
        for column, key, fmt in schema:
            row.append(_cell(item, column, key, fmt))
        table.add_row(row)

    return table


def make_list_to_table(schema, header=True, align=None):
    """Return list to table function given schema."""
    return lambda items: list_to_table(items, schema, header, align)


class AppPrettyFormatter(object):
    """Pretty table app formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        services_restart_tbl = make_dict_to_table([
            ('limit', None, None),
            ('interval', None, None),
        ])

        def _command_fmt(cmd):
            return wrap_words(cmd.split(), 40, ' ', '\n   ')

        services_tbl = make_list_to_table([
            ('name', None, None),
            ('root', None, None),
            ('restart', None, services_restart_tbl),
            ('command', None, _command_fmt),
        ])

        endpoints_tbl = make_list_to_table([
            ('name', None, None),
            ('port', None, None),
            ('proto', None, lambda proto: proto if proto else 'tcp'),
            ('type', None, None),
        ])

        environ_tbl = make_list_to_table([
            ('name', None, None),
            ('value', None, None),
        ])

        vring_rules_tbl = make_list_to_table([
            ('pattern', None, None),
            ('endpoints', None, ','.join),
        ])

        vring_tbl = make_dict_to_table([
            ('cells', None, ','.join),
            ('rules', None, vring_rules_tbl),
        ])

        ephemeral_tbl = make_dict_to_table([
            ('tcp', None, None),
            ('udp', None, None),
        ])

        affinity_limits_tbl = make_dict_to_table([
            ('pod', None, None),
            ('rack', None, None),
            ('server', None, None),
        ])

        schema = [
            ('name', '_id', None),
            ('memory', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('tickets', None, None),
            ('features', None, None),
            ('identity-group', 'identity_group', None),
            ('schedule-once', 'schedule_once', None),
            ('shared-ip', 'shared_ip', None),
            ('ephemeral-ports', 'ephemeral_ports', ephemeral_tbl),
            ('services', None, services_tbl),
            ('endpoints', None, endpoints_tbl),
            ('environ', None, environ_tbl),
            ('vring', None, vring_tbl),
            ('passthrough', None, '\n'.join),
            ('data-retention-timeout', 'data_retention_timeout', None),
            ('lease', 'lease', None),
            ('affinity', 'affinity', None),
            ('affinity-limits', 'affinity_limits', affinity_limits_tbl),
        ]

        format_item = make_dict_to_table(schema)

        format_list = make_list_to_table([
            ('name', '_id', None),
            ('memory', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('tickets', None, None),
            ('features', None, None),
        ])

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class AppMonitorPrettyFormatter(object):
    """Pretty table app monitor formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('monitor', '_id', None),
                  ('count', 'count', None),
                  ('suspend until', 'suspend_until', fmt_time)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class IdentityGroupPrettyFormatter(object):
    """Pretty table identity group formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('identity-group', '_id', None),
                  ('count', 'count', None)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class ServerPrettyFormatter(object):
    """Pretty table server formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        schema = [
            ('name', '_id', None),
            ('cell', None, None),
            ('traits', None, None),
            ('partition', None, None),
            ('data', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class ServerNodePrettyFormatter(object):
    """Pretty table server (scheduler) node formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('name', None, None),
                  ('memory', None, None),
                  ('cpu', None, None),
                  ('disk', None, None),
                  ('partition', None, None),
                  ('parent', None, None),
                  ('traits', None, None),
                  ('state', None, None),
                  ('since', None, fmt_time)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class LdapSchemaPrettyFormatter(object):
    """Pretty table ldap schema formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        attr_tbl = make_list_to_table([
            ('name', None, None),
            ('desc', None, None),
            ('type', None, None),
            ('ignore_case', None, None),
        ])

        objcls_tbl = make_list_to_table([
            ('name', None, None),
            ('desc', None, None),
            ('must', None, None),
            ('may', None, make_wrap_words(40)),
        ])

        schema_tbl = make_dict_to_table([
            ('dn', None, None),
            ('attributes', 'attributeTypes', attr_tbl),
            ('objects', 'objectClasses', objcls_tbl),
        ])

        return schema_tbl(item)


class BucketPrettyFormatter(object):
    """Pretty table bucket formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('name', None, None),
                  ('parent', None, None),
                  ('traits', None, None)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class CellPrettyFormatter(object):
    """Pretty table cell formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        masters_tbl = make_list_to_table([
            ('idx', None, None),
            ('hostname', None, None),
            ('zk-client-port', None, None),
            ('zk-jmx-port', None, None),
            ('zk-followers-port', None, None),
            ('zk-election-port', None, None),
        ])

        partitions_tbl = make_list_to_table([
            ('id', 'partition', None),
            ('cpu', None, None),
            ('disk', None, None),
            ('memory', None, None),
            ('system', 'systems', None),
            ('down threshold', 'down-threshold', None),
            ('reboot schedule', 'reboot-schedule', None),
        ])

        schema = [
            ('name', '_id', None),
            ('version', None, None),
            ('root', None, None),
            ('username', None, None),
            ('location', None, None),
            ('archive-server', None, None),
            ('archive-username', None, None),
            ('ssq-namespace', None, None),
            ('masters', None, masters_tbl),
            ('partitions', None, partitions_tbl),
            ('data', None, yaml.dump),
        ]

        format_item = make_dict_to_table(schema)

        format_list = make_list_to_table([
            ('name', '_id', None),
            ('location', None, None),
            ('version', None, None),
            ('username', None, None),
            ('root', None, None),
        ])

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class DNSPrettyFormatter(object):
    """Pretty table critical DNS formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('name', '_id', None),
                  ('location', None, None),
                  ('servers', 'server', '\n'.join),
                  ('rest-servers', 'rest-server', '\n'.join),
                  ('zkurl', None, None),
                  ('fqdn', None, None),
                  ('ttl', None, None),
                  ('nameservers', None, '\n'.join)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table([
            ('name', '_id', None),
            ('location', None, None),
            ('fqdn', None, None),
            ('servers', 'server', ','.join),
        ])

        if isinstance(item, list):
            return format_list(item)

        return format_item(item)


class AppGroupPrettyFormatter(object):
    """Pretty table App Groups formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [('name', '_id', None),
                  ('type', 'group-type', None),
                  ('cells', None, None),
                  ('pattern', None, None),
                  ('endpoints', None, None),
                  ('data', None, None)]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class TenantPrettyFormatter(object):
    """Pretty table tenant formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('tenant', ['_id', 'tenant'], None),
            ('system', 'systems', None),
        ]

        format_item = make_dict_to_table(
            schema +
            [('allocations', 'allocations', AllocationPrettyFormatter.format)]
        )
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class AllocationPrettyFormatter(object):
    """Pretty table allocation formatter."""
    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        assignments_table = make_list_to_table([
            ('pattern', None, None),
            ('priority', None, None),
        ])

        cell_tbl = make_list_to_table([
            ('cell', 'cell', None),
            ('partition', None, None),
            ('rank', None, None),
            ('rank-adjustment', 'rank_adjustment', None),
            ('max-utilization', 'max_utilization', None),
            ('memory', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('traits', None, '\n'.join),
            ('assignments', None, assignments_table),
        ])

        schema = [
            ('environment', None, None),
            ('reservations', None, cell_tbl),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class InstanceStatePrettyFormatter(object):
    """Pretty table instance state formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('name', None, None),
            ('state', None, None),
            ('host', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema, header=False)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class InstanceFinishedStatePrettyFormatter(object):
    """Pretty table instance finished state formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('name', None, None),
            ('state', None, None),
            ('host', None, None),
            ('when', None, None),
            ('details', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema, header=False)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class EndpointPrettyFormatter(object):
    """Pretty table endpoint formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        def _fmt_state(state):
            """Format endpoint state."""
            return '-' if state is None else 'up' if state else 'down'

        schema = [
            ('name', None, None),
            ('proto', None, None),
            ('endpoint', None, None),
            ('hostport', None, None),
            ('state', None, _fmt_state),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema, header=False)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class PartitionPrettyFormatter(object):
    """Pretty table partition formatter."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        schema = [
            ('id', 'partition', None),
            ('cell', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('memory', None, None),
            ('system', 'systems', None),
            ('down threshold', 'down-threshold', None),
            ('reboot schedule', 'reboot-schedule', None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class HAProxyPrettyFormatter(object):
    """Pretty table formatter for HAProxy."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('server', '_id', None),
            ('cell', 'cell', None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        return format_item(item)


class CronPrettyFormatter(object):
    """Pretty table formatter for cron jobs."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('id', '_id', None),
            ('resource', None, None),
            ('event', None, None),
            ('action', None, None),
            ('count', None, None),
            ('expression', None, None),
            ('next_run_time', None, None),
            ('timezone', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class AllocationQueuePrettyFormatter(object):
    """Pretty table formatter for allocation queue."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('pos', None, None),
            ('allocation', 'alloc', None),
            ('name', None, None),
            ('rank', None, None),
            ('memory', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('util0', None, fmt_utilization),
            ('util1', None, fmt_utilization),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema, align={'pos': 'r',
                                                        'rank': 'r',
                                                        'memory': 'r',
                                                        'cpu': 'r',
                                                        'disk': 'r',
                                                        'util0': 'r',
                                                        'util1': 'r'})

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class PlacementPrettyFormatter(object):
    """Pretty table formatter for explain-placement."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        def _status(value):
            """Return formatted bool."""
            return '.' if value else 'x'

        def _up_down(value):
            """Return boolean as up/down."""
            return 'up' if value else 'down'

        schema = [
            ('name', None, None),
            ('server', None, _status),
            ('state', None, _up_down),
            ('partition', None, _status),
            ('traits', 'traits', _status),
            ('affinity', None, _status),
            ('lifetime', None, _status),
            ('memory', None, _status),
            ('cpu', None, _status),
            ('disk', None, _status),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SchedulerServersPrettyFormatter(object):
    """Pretty table formatter for scheduler view servers."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('name', None, None),
            ('location', None, None),
            ('partition', None, None),
            ('state', None, None),
            ('valid_until', None, None),
            ('traits', None, None),
            ('mem', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('mem_free', None, None),
            ('cpu_free', None, None),
            ('disk_free', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SchedulerAppsPrettyFormatter(object):
    """Pretty table formatter for scheduler view apps."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('instance', None, None),
            ('partition', None, None),
            ('allocation', None, None),
            ('rank', None, None),
            ('util0', None, fmt_utilization),
            ('util1', None, fmt_utilization),
            ('affinity', None, None),
            ('identity_group', None, None),
            ('identity', None, None),
            ('lease', None, None),
            ('expires', None, None),
            ('data_retention', None, None),
            ('mem', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('server', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema, align={'util0': 'r',
                                                        'util1': 'r'})

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SchedulerAllocsPrettyFormatter(object):
    """Pretty table formatter for scheduler view allocs."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('name', None, None),
            ('partition', None, None),
            ('rank', None, None),
            ('rank_adj', None, None),
            ('mem', None, None),
            ('cpu', None, None),
            ('disk', None, None),
            ('traits', None, None),
            ('max_util', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SchedulerRebootsPrettyFormatter(object):
    """Pretty table formatter for scheduler view reboots."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('server', None, None),
            ('valid-until', None, None),
            ('days-left', None, None),
        ]

        format_item = make_dict_to_table(schema)
        format_list = make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)
