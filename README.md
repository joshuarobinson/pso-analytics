# pso-analytics

## UPDATED: PSO Explorer!

This tool has been significantly improved and relaunched as [PSO Explorer](https://blog.purestorage.com/pure-service-orchestrator-explorer-for-container-storage-visibility/).

## PSO-Analytics

Storage analytics for Kubernetes: for a detailed description see my [accompanying blog post](https://medium.com/@joshua_robinson/pso-analytics-visibility-into-how-kubernetes-applications-use-storage-e7bda52c3bf).

## Problem Statement

When consuming storage in Kubernetes through PersistentVolumeClaims and using a
CSI provisioner, there is no visibility into the storage layer itself. The only
information visible from Kubernetes is the capacity allocation per
PersistentVolume, which leaves almost all useful storage administration
questions unanswered:
 * How much storage does this cluster use on each backend device?
 * How much storage does each statefulset use in total?
 * How much storage usage in each namespace?
 * What is the data reduction across any of the above dimensions?
 * What is the performance across any of the above dimensions?

The origin of this problem is that Kubernetes has only half the necessary info,
e.g. labels and statefulsets. And the storage system has the other half: space
usage, data reduction, and performance stats. To have full visibility into the
storage usage of your kubernetes applications, you need to merge these two
views.

## PSO-analytics v0.1

PSO-analytics is a deployment that periodically correlates storage usage and data reduction rates across multiple dimensions:
* statefulset
* storageclassname
* backend device (FlashArrays and FlashBlades)
* label
* namespace

To install in the 'pso-analytics' namespace:
```
kubectl apply -f https://raw.githubusercontent.com/joshuarobinson/pso-analytics/master/pso-analytics.yaml
```

Download and modify the yaml to change the namespace or periodicity of output.

To view the output:
```
kubectl logs -n=pso-analytics deployment.apps/pso-analytics
```

## PSO-analytics v0.2

Added support for a Prometheus endpoint via the command line flag '--prometheus' on port 9492.

Configure Prometheus to scrape pso-analytics as follows:
```
    scrape_configs:
      - job_name: 'pso-analytics-monitor'
        static_configs:
        - targets: ['pso-analytics:9492']
```

Limitations:
* Needs ability to LIST all pods in all namespaces in order to auto-discover PSO
* Output is rigid and not easy to parse, query, or visualize
* Many other interesting aggregations and top 10s missing
* Performance information not included
