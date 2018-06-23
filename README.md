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


## Resources

StackStorm:
- [Docs](https://docs.stackstorm.com/)

RIPE/RIPE Atlas
- [RIPE Atlas CLI Tools](https://github.com/RIPE-NCC/ripe-atlas-tools)
- [RIPE Atlas Python Library](https://github.com/RIPE-NCC/ripe-atlas-cousteau)
- [RIPE Atlas API Docs](https://atlas.ripe.net/docs/api/v2/manual/)
- [RIPE Atlas python tools docs](https://ripe-atlas-cousteau.readthedocs.io/en/latest/)
