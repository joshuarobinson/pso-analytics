# pso-analytics

## v0.1

PSO-analytics is a deployment that periodically correlates storage usage and data reduction rates across multiple dimensions:
* statefulsets
* storageclassnames
* labels
* namespaces

To install in the 'pso-analytics' namespace:
```
kubectl apply -f https://raw.githubusercontent.com/joshuarobinson/pso-analytics/master/pso-analytics.yaml
```

Download and modify the yaml to change the namespace or periodicity of output.

To view the output:
```
kubectl logs -f -n=pso-analytics deployment.apps/pso-analytics
```

Limitations:
* Output is rigid and not easy to parse, query, or visualize
* Many other interesting aggregations and top 10s missing
* Performance information not included
