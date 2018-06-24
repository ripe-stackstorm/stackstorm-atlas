# RIPE Atlas Pack

Pack for working with RIPE Atlas (will elaborate here later)

## Installation

While developing this pack, it might be useful to rsync local directories (for instance this repo) into your st2vagrant VM. See the below for an example:

```bash
config.vm.synced_folder "~/Code/StackStorm/stackstorm-atlas", "/opt/stackstorm/packs/atlas", type: "rsync", rsync__exclude: [".git/", "virtualenv"]
```

Then, inside the VM you'll want to run:

```bash
st2ctl reload
```

## Actions

`get_measurement_result`:

```bash
vagrant@st2vagrant:~$ st2 run atlas.get_measurement_result measurement_id=14680108
id: 5b2e4478c4da5f10bb1f9f21
status: succeeded
parameters:
  measurement_id: '14680108'
result:
  exit_code: 0
  result:
    latency_avg: 38.78349649659795
    raw_results:
    - af: 4
      avg: 13.590395
      dst_addr: 37.252.172.53
      dst_name: adx.adnxs.com
      dup: 0
      from: 193.96.224.61
```


## Resources

StackStorm:

- [Docs](https://docs.stackstorm.com/)

RIPE/RIPE Atlas

- [RIPE Atlas CLI Tools](https://github.com/RIPE-NCC/ripe-atlas-tools)
- [RIPE Atlas Python Library](https://github.com/RIPE-NCC/ripe-atlas-cousteau)
- [RIPE Atlas API Docs](https://atlas.ripe.net/docs/api/v2/manual/)
- [RIPE Atlas python tools docs](https://ripe-atlas-cousteau.readthedocs.io/en/latest/)
- [List of public measurements](https://atlas.ripe.net/measurements/?page=1#tab-ping)