## What is this?

Weaver is a plugin for [Cuckoo Sandbox](https://github.com/cuckoobox/cuckoo) to check the health of your sandbox environment. Give it a few samples and it will wrap those up and digest them - telling you if anything was missed from your dynamic analysis.

## Install
Get the dependencies:
`pip install -r requirements.txt`

Point your config to your malware samples - by default [it lives here](https://github.com/bschmoker/weaver/blob/master/sample.cfg) and pull samples from [this location](/samples)

Run the daemon:
`python weaver`
