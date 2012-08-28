from blinker import Namespace


_signals = Namespace()

sarge_initializing = _signals.signal('sarge-initializing')
instance_configuring = _signals.signal('instance-configuring')
instance_will_start = _signals.signal('instance-will-start')
instance_has_stopped = _signals.signal('instance-has-stopped')
instance_will_be_destroyed = _signals.signal('instance-will-be-destroyed')
