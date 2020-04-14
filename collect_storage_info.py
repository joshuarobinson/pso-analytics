import kubernetes
import purestorage
import purity_fb
import tabulate

import argparse
import base64
import copy
import json
import os
import re
import urllib3


# Helper to output byte values in human readable format.
def as_human_readable(input_bytes):
    if input_bytes < 1024:
        return str(input_bytes)
    elif input_bytes < (1024 ** 2):
        return str(round(input_bytes / 1024, 1)) + "K"
    elif input_bytes < (1024 ** 3):
        return str(round(input_bytes / (1024 ** 2), 1)) + "M"
    elif input_bytes < (1024 ** 4):
        return str(round(input_bytes / (1024 ** 3), 1)) + "G"
    elif input_bytes < (1024 ** 5):
        return str(round(input_bytes / (1024 ** 4), 1)) + "T"
    elif input_bytes < (1024 ** 6):
        return str(round(input_bytes / (1024 ** 5), 1)) + "P"
    else:
        return str(round(input_bytes / (1024 ** 6), 1)) + "E"


def sum_volume_records(x, y):
    return {k: x.get(k, 0) + y.get(k, 0) for k in set(x) | set(y)}

def prettify_record(r):
    drr = round(r["logical_bytes"] / r["physical_bytes"], 1) if r["physical_bytes"] > 0 else 1.0

    newr = {"drr": drr}
    newr.update(r)
    for l in ["logical_bytes", "physical_bytes", "provisioned_bytes"]:
        newr[l] = as_human_readable(newr[l])
    return newr



###############################################################################

parser = argparse.ArgumentParser()

parser.add_argument('--output', choices=['table', 'json'],
                    default='table',
                    help='Output format.')
args = parser.parse_args()

#========= Login to Kubernetes cluster ======================

# Configs can be set in Configuration class directly or using helper utility
kubernetes.config.load_incluster_config()

v1 = kubernetes.client.CoreV1Api()

# Collect state about each PVC found in the system.
pvcs = {}
ret = v1.list_persistent_volume_claim_for_all_namespaces(watch=False)
for i in ret.items:
    pvcs[i.metadata.uid] = {"name": i.metadata.name, "namespace":
        i.metadata.namespace, "storageclass": i.spec.storage_class_name,
        "labels": i.metadata.labels}

# To group PVCs by StatefulSet, create regexes that matches the naming
# convention for the PVCs that belong to VolumeClaimTemplates.
ss_regexes = {}
ret = kubernetes.client.AppsV1Api().list_stateful_set_for_all_namespaces(watch=False)
for i in ret.items:
    if i.spec.volume_claim_templates:
        for vct in i.spec.volume_claim_templates:
            ssname = i.metadata.name + "." + i.metadata.namespace
            ss_regexes[ssname] = re.compile(vct.metadata.name + "-" + i.metadata.name + "-[0-9]+")

# Search for PURE_K8S_NAMESPACE
pso_namespace = ""
pso_prefix = ""
ret = v1.list_pod_for_all_namespaces(watch=False)
for i in ret.items:
    for c in i.spec.containers:
        if c.env:
            for e in c.env:
                if e.name == "PURE_K8S_NAMESPACE":
                    pso_prefix = e.value
                    pso_namespace = i.metadata.namespace
                    break

if not pso_namespace:
    print("Did not find PSO, exiting")
    exit(1)

# Find the secret associated with the pure-provisioner in order to find the
# login info for all FlashArrays and FlashBlades.
flashblades={}
flasharrays={}

secrets = v1.read_namespaced_secret("pure-provisioner-secret", pso_namespace)
rawbytes = base64.b64decode(secrets.data['pure.json'])
purejson = json.loads(rawbytes.decode("utf-8"))
pso_namespace = i.metadata.namespace
flashblades = purejson["FlashBlades"] if "FlashBlades" in purejson else {}
flasharrays = purejson["FlashArrays"] if "FlashArrays" in purejson else {}


# Begin collecting and correlating volume information from the backends.
vols = []

# Disable warnings due to unsigned SSL certs.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#========= Login to FlashArrays ======================

for fajson in flasharrays:
    fa = purestorage.FlashArray(fajson["MgmtEndPoint"], api_token=fajson["APIToken"])

    try:
        for vol in fa.list_volumes(names=[pso_prefix + "*"], space=True):
            assert vol["name"].startswith(pso_prefix + "-pvc-")
            uid = vol["name"].replace(pso_prefix + "-pvc-", "")

            if uid not in pvcs:
                print("Found orphan PersistentVolume: " + uid + " on FlashArray " + fajson["MgmtEndPoint"])
                continue

            pvc = pvcs[uid]

            tags = {"all": "all",
                    "storageclass": pvc["storageclass"],
                    "namespace": pvc["namespace"],
                    "backend": "FA " + fajson["MgmtEndPoint"]}
            if pvc["labels"]:
                for l in pvc["labels"]:
                    tags["label/" + l] = pvc["labels"][l]
            for ssname,rgx in ss_regexes.items():
                if rgx.match(pvc["name"]):
                    tags["statefulset"] = ssname

            vol = {"uid": uid,
                   "logical_bytes": vol["total"],
                   "physical_bytes": vol["total"] / vol["data_reduction"],
                   "provisioned_bytes": vol["size"],
                   "tags": tags}

            vols.append(vol)

    except:
        pass


#========= Login to FlashBlades ======================

for fbjson in flashblades:
    fb = purity_fb.PurityFb(fbjson["MgmtEndPoint"],
                            api_token=fbjson["APIToken"])

    res = fb.file_systems.list_file_systems(filter="name='" + pso_prefix + "*'")
    for fs in res.items:
        assert fs.name.startswith(pso_prefix + "-pvc-")
        uid = fs.name.replace(pso_prefix + "-pvc-", "")

        if uid not in pvcs:
            print("Found orphan PersistentVolume: " + uid + " on FlashBlade " + fbjson["MgmtEndPoint"])
            continue

        pvc = pvcs[uid]

        tags = {"all": "all",
                "storageclass": pvc["storageclass"],
                "namespace": pvc["namespace"],
                "backend": "FB " + fbjson["MgmtEndPoint"]}
        if pvc["labels"]:
            for l in pvc["labels"]:
                tags["label/" + l] = pvc["labels"][l]
        for ssname,rgx in ss_regexes.items():
            if rgx.match(pvc["name"]):
                tags["statefulset"] = ssname

        vol = {"uid": uid,
               "logical_bytes": fs.space.virtual,
               "physical_bytes": fs.space.total_physical,
               "provisioned_bytes": fs.provisioned,
               "tags": tags}

        vols.append(vol)

#========= Print out Results ======================

if args.output == 'table':
    # Grab the unique list of keys in the tags across all volumes.
    tablenames = list(set([y for x in [list(v["tags"].keys()) for v in vols] for y in x]))

    for tab in tablenames:
        thistab = {}
        print("\n==== {} =====".format(tab))
        for v in vols:
            if tab in v["tags"]:
                key = v["tags"][tab]
                newrow = {"logical_bytes": v["logical_bytes"],
                          "physical_bytes": v["physical_bytes"],
                          "provisioned_bytes": v["provisioned_bytes"],
                          "volume_count": 1}
                thistab[key] = sum_volume_records(thistab[key], newrow) if key in thistab else copy.copy(newrow)

        # Flatten to a list and put the "name" back into to the dict. For tabulate
        finaltab = [{"name": k, **prettify_record(thistab[k])} for k in thistab.keys()]
        print(tabulate.tabulate(finaltab, headers="keys"))

elif args.output == 'json':
    for v in vols:
        print(v)
