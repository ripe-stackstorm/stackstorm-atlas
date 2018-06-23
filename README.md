# RIPE Atlas Pack

Pack for working with RIPE Atlas (will elaborate here later)

## Installation

While developing this pack, it might be useful to rsync local directories (for instance this repo) into your st2vagrant VM. See the below for an example:

```
config.vm.synced_folder "~/Code/StackStorm/stackstorm-atlas", "/opt/stackstorm/packs/atlas", type: "rsync", rsync__exclude: [".git/", "virtualenv"]
```

Then, inside the VM you'll want to run:

```
st2ctl reload
```
