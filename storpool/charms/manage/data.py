# Copyright (c) 2018  StorPool
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Classes representing various Juju charm data structures.
"""


from typing import Any, Dict, List, Optional, Union

from mypy_extensions import TypedDict


ObjectStatus = TypedDict('ObjectStatus', {
    'current': str,
    'since': str,
    'message': str,
    'version': str,
})


Container = TypedDict('Container', {
    'juju-status': ObjectStatus,
    'dns-name': str,
    'ip-addresses': List[str],
    'instance-id': str,
    'machine-status': ObjectStatus,
    'series': str,
    'constraints': str,

    '_mid': str,
    '_mtype': str,
    '_type': Optional[str],
    '_units': Dict[str, Any],  # actually Unit
    '_mach': Any  # actually Machine
})


Interface = TypedDict('Interface', {
    'ip-addresses': List[str],
    'mac-address': str,
    'gateway': str,
    'space': str,
    'is-up': bool,
})


Machine = TypedDict('Machine', {
    'juju-status': ObjectStatus,
    'dns-name': str,
    'ip-addresses': List[str],
    'instance-id': str,
    'machine-status': ObjectStatus,
    'series': str,
    'network-interfaces': Dict[str, Interface],
    'containers': Dict[str, Container],
    'constraints': str,

    '_mid': str,
    '_mtype': str,
    '_type': Optional[str],
    '_units': Dict[str, Any],  # actually Unit
})


GenericMachine = Union[Machine, Container]


Unit = TypedDict('Unit', {
    'workload-status': ObjectStatus,
    'juju-status': ObjectStatus,
    'leader': bool,
    'machine': str,
    'public-address': str,

    '_name': str,
    '_mach': GenericMachine,
    '_app': Any,  # actually Application
})


Application = TypedDict('Application', {
    'charm-name': str,
    'charm-rev': int,
    'series': str,
    'units': Dict[str, Unit],

    '_name': str,
    '_type': Optional[str],
})


StatusController = TypedDict('StatusController', {
    'timestamp': str,
})


SPStatusMetaApps = TypedDict('SPStatusMetaApps', {
    'by_charm': Dict[str, Dict[str, Application]],
    'by_type': Dict[str, Dict[str, Application]],
})


SPStatusMetaMachines = TypedDict('SPStatusMetaMachines', {
    'all': Dict[str, GenericMachine],
    'by_type': Dict[str, Dict[str, GenericMachine]],
})


SPStatusStorPool = TypedDict('SPStatusStorPool', {
    'chosen_charm': Dict[str, str],
    'machines': Dict[str, List[str]],
})


SPStatusMeta = TypedDict('SPStatusMeta', {
    'applications': SPStatusMetaApps,
    'machines': SPStatusMetaMachines,
    'sp': SPStatusStorPool,
})


Status = TypedDict('Status', {
    'applications': Dict[str, Application],
    'controller': StatusController,
    'machines': Dict[str, Machine],

    '_meta': SPStatusMeta,
})
