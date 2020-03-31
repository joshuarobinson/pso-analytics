# pso-analytics

## v0.1

PSO-analytics is a deployment that periodically correlates storage usage and data reduction rates across multiple dimensions:
* statefulsets
* storageclassnames
* labels
* namespaces

To install:
```
kubectl apply -f https://raw.githubusercontent.com/joshuarobinson/pso-analytics/master/pso-analytics.yaml
```

To view the output:
```
kubectl logs -f deployment.apps/pso-analytics
```

Limitations:
* Overly invasive privileges granted (all secrets visible)
* Installs in the default namespace
* Output is rigid and not easy to parse, query, or visualize
* Many other interesting aggregations and top 10s missing
* Performance information not included
