# EKS Cluster Upgrade

|                            |                           Value                           |
| :------------------------- | :-------------------------------------------------------: |
| Amazon EKS cluster         |                 `mulesoft-obs-demo`                      |
| Current version            |                 `v1.24`                  |
| Target version             |                  `v1.25`                  |
| EKS Managed nodegroup(s)  |  ✅   |
| Self-Managed nodegroup(s) |  ➖  |
| Fargate profile(s)         |      ➖      |

## Table of Contents

- [Upgrade the Control Plane](#upgrade-the-control-plane)
    - [Control Plane Pre-Upgrade](#control-plane-pre-upgrade)
    - [Control Plane Upgrade](#control-plane-upgrade)
- [Upgrade EKS Addons](#upgrade-eks-addons)
    - [Addon Pre-Upgrade](#addon-pre-upgrade)
    - [Addon Upgrade](#addon-upgrade)
- [Upgrade the Data Plane](#upgrade-the-data-plane)
    - [Data Plane Pre-Upgrade](#data-plane-pre-upgrade)
        - [EKS Managed Nodegroup](#eks-managed-nodegroup)
- [Post-Upgrade](#post-upgrade)
- [References](#references)


## Upgrade the Control Plane

### Control Plane Pre-Upgrade

1. Review the following resources for affected changes in the next version of Kubernetes:

    - ‼️ [Kubernetes `1.25` API deprecations](https://kubernetes.io/docs/reference/using-api/deprecation-guide/#v1-25)
    - ℹ️ [Kubernetes `1.25` release announcement](https://kubernetes.io/blog/2022/08/23/kubernetes-v1-25-release/)
    - ℹ️ [EKS `1.25` release notes](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html#kubernetes-1.25)

2. Per the [Kubernetes version skew policy](https://kubernetes.io/releases/version-skew-policy/#supported-version-skew), the `kubelet` version must not be newer than `kube-apiserver`, and may be up to two minor versions older. It is recommended that the nodes in the data plane are aligned with the same minor version as the control plane before upgrading.

    <details>
    <summary>📌 CLI Example</summary>

    Ensure you have updated your `kubeconfig` locally before executing the following commands:

    ```sh
    aws eks update-kubeconfig --region us-east-1  --name mulesoft-obs-demo
    ```

    Control plane Kubernetes version:

    ```sh
    kubectl version --short

    # Output (truncated)
    Server Version: v1.23.14-eks-ffeb93d
    ```

    Node(s) Kubernetes version(s):

    ```sh
    kubectl get nodes

    # Output
    NAME                                  STATUS   ROLES    AGE   VERSION
    fargate-ip-10-0-14-253.ec2.internal   Ready    <none>   9h    v1.23.14-eks-a1bebd3 ✅ # Ready to upgrade
    fargate-ip-10-0-7-182.ec2.internal    Ready    <none>   9h    v1.23.14-eks-a1bebd3 ✅ # Ready to upgrade
    ip-10-0-14-102.ec2.internal           Ready    <none>   9h    v1.22.15-eks-fb459a0 ⚠️ # Recommended to upgrade first
    ip-10-0-27-61.ec2.internal            Ready    <none>   9h    v1.22.15-eks-fb459a0 ⚠️ # Recommended to upgrade first
    ip-10-0-41-36.ec2.internal            Ready    <none>   9h    v1.21.14-eks-fb459a0 ❌ # Requires upgrade first
    ```
    </details>

    #### Check [[K8S001]](https://clowdhaus.github.io/eksup/info/checks/#k8s001)
        ✅ - No reported findings regarding version skew between the control plane and nodes

3. Verify that there are at least 5 free IPs in the VPC subnets used by the control plane. Amazon EKS creates new elastic network interfaces (ENIs) in any of the subnets specified for the control plane. If there are not enough available IPs, then the upgrade will fail (your control plane will stay on the prior version).

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    aws ec2 describe-subnets --region us-east-1 --subnet-ids \
        $(aws eks describe-cluster --region us-east-1 --name mulesoft-obs-demo \
      --query 'cluster.resourcesVpcConfig.subnetIds' --output text) \
      --query 'Subnets[*].AvailableIpAddressCount'
    ```

    </details>

    #### Check [[EKS001]](https://clowdhaus.github.io/eksup/info/checks/#eks001)
        ✅ - There is sufficient IP space in the subnets provided

4. Ensure the cluster is free of any health issues as reported by Amazon EKS. If there are any issues, resolution of those issues is required before upgrading the cluster. Note - resolution in some cases may require creating a new cluster. For example, if the cluster primary security group was deleted, at this time, the only course of remediation is to create a new cluster and migrate any workloads over to that cluster (treated as a blue/green cluster upgrade).

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    aws eks describe-cluster --region us-east-1 --name mulesoft-obs-demo \
        --query 'cluster.health'
    ```

    </details>

    #### Check [[EKS002]](https://clowdhaus.github.io/eksup/info/checks/#eks002)
        ✅ - There are no reported health issues on the cluster control plane

5. Ensure the EKS addons in use are using a version that is supported by the intended target Kubernetes version. If an addon is not compatible with the intended target Kubernetes version, upgrade the addon to a version that is compatible before upgrading the cluster.

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    for ADDON in $(aws eks list-addons --cluster-name mulesoft-obs-demo \
        --region us-east-1 --query 'addons[*]' --output text); do
      CURRENT=$(aws eks describe-addon --cluster-name mulesoft-obs-demo --region us-east-1 \
        --addon-name ${ADDON} --query 'addon.addonVersion' --output text)
      LATEST=$(aws eks describe-addon-versions --region us-east-1 --addon-name ${ADDON} \
        --kubernetes-version 1.25 --query 'addons[0].addonVersions[0].addonVersion' --output text)
      LIST=$(aws eks describe-addon-versions --region us-east-1 --addon-name ${ADDON} \
        --kubernetes-version 1.25 --query 'addons[0].addonVersions[*].addonVersion')

      echo "${ADDON} current version: ${CURRENT}"
      echo "${ADDON} next latest version: ${LATEST}"
      echo "${ADDON} next available versions: ${LIST}"
    done
    ```

    </details>

    #### Check [[EKS005]](https://clowdhaus.github.io/eksup/info/checks/#eks005)
        |    | NAME               | CURRENT            | LATEST             | DEFAULT            |
        |----|--------------------|--------------------|--------------------|--------------------|
        | ⚠️  | adot               | v0.66.0-eksbuild.1 | v0.70.0-eksbuild.1 | v0.70.0-eksbuild.1 |
        | ⚠️  | aws-ebs-csi-driver | v1.16.0-eksbuild.1 | v1.17.0-eksbuild.1 | v1.17.0-eksbuild.1 |
        | ⚠️  | coredns            | v1.8.7-eksbuild.3  | v1.9.3-eksbuild.2  | v1.9.3-eksbuild.2  |
        | ❌ | kube-proxy         | v1.24.7-eksbuild.2 | v1.25.6-eksbuild.2 | v1.25.6-eksbuild.1 |
        | ❌ | vpc-cni            | v1.11.4-eksbuild.1 | v1.12.6-eksbuild.1 | v1.12.2-eksbuild.1 |


5. Check Kubernetes API versions currently in use and ensure any versions that are removed in the next Kubernetes release are updated prior to upgrading the cluster. There are several open source tools that can help you identify deprecated API versions in your Kubernetes manifests. The following open source projects support scanning both your cluster as well as manifest files to identify deprecated and/or removed API versions:

    - https://github.com/FairwindsOps/pluto
    - https://github.com/doitintl/kube-no-trouble

### Control Plane Upgrade

ℹ️ [Updating an Amazon EKS cluster Kubernetes version](https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html)

When upgrading the control plane, Amazon EKS performs standard infrastructure and readiness health checks for network traffic on the new control plane nodes to verify that they're working as expected. If any of these checks fail, Amazon EKS reverts the infrastructure deployment, and your cluster control plane remains on the prior Kubernetes version. Running applications aren't affected, and your cluster is never left in a non-deterministic or unrecoverable state. Amazon EKS regularly backs up all managed clusters, and mechanisms exist to recover clusters if necessary.

1. Upgrade the control plane to the next Kubernetes minor version:

    ```sh
    aws eks update-cluster-version --region us-east-1 --name mulesoft-obs-demo \
        --kubernetes-version 1.25
    ```

2. Wait for the control plane to finish upgrading before proceeding with any further modifications. The cluster status will change to `ACTIVE` once the upgrade is complete.

    ```sh
    aws eks describe-cluster --region us-east-1 --name mulesoft-obs-demo \
        --query 'cluster.status'
    ```

## Upgrade the Data Plane

### Data Plane Pre-Upgrade

1. Ensure applications and services running on the cluster are setup for high-availability to minimize and avoid disruption during the upgrade process.

    🚧 TODO - fill in analysis results

    #### Check [[K8S002]](https://clowdhaus.github.io/eksup/info/checks/#k8s002)
        |    | NAME                                      | NAMESPACE                     | KIND       | REPLICAS |
        |----|-------------------------------------------|-------------------------------|------------|----------|
        | ❌ | adot-collector                            | adot-collector-kubeprometheus | Deployment | 1        |
        | ❌ | cert-manager                              | cert-manager                  | Deployment | 1        |
        | ❌ | cert-manager-cainjector                   | cert-manager                  | Deployment | 1        |
        | ❌ | cert-manager-webhook                      | cert-manager                  | Deployment | 1        |
        | ❌ | knative-operator                          | default                       | Deployment | 1        |
        | ❌ | operator-webhook                          | default                       | Deployment | 1        |
        | ❌ | istio-ingressgateway                      | istio-system                  | Deployment | 1        |
        | ❌ | istiod                                    | istio-system                  | Deployment | 1        |
        | ❌ | karpenter                                 | karpenter                     | Deployment | 2        |
        | ❌ | hello-00001-deployment                    | knative-demo                  | Deployment | 0        |
        | ❌ | eventing-controller                       | knative-eventing              | Deployment | 1        |
        | ❌ | eventing-webhook                          | knative-eventing              | Deployment | 1        |
        | ❌ | imc-controller                            | knative-eventing              | Deployment | 1        |
        | ❌ | imc-dispatcher                            | knative-eventing              | Deployment | 1        |
        | ❌ | mt-broker-controller                      | knative-eventing              | Deployment | 1        |
        | ❌ | mt-broker-filter                          | knative-eventing              | Deployment | 1        |
        | ❌ | mt-broker-ingress                         | knative-eventing              | Deployment | 1        |
        | ❌ | pingsource-mt-adapter                     | knative-eventing              | Deployment | 0        |
        | ❌ | activator                                 | knative-serving               | Deployment | 1        |
        | ❌ | autoscaler                                | knative-serving               | Deployment | 1        |
        | ❌ | autoscaler-hpa                            | knative-serving               | Deployment | 1        |
        | ❌ | controller                                | knative-serving               | Deployment | 1        |
        | ❌ | domain-mapping                            | knative-serving               | Deployment | 1        |
        | ❌ | domainmapping-webhook                     | knative-serving               | Deployment | 1        |
        | ❌ | net-istio-controller                      | knative-serving               | Deployment | 1        |
        | ❌ | net-istio-webhook                         | knative-serving               | Deployment | 1        |
        | ❌ | webhook                                   | knative-serving               | Deployment | 1        |
        | ❌ | cluster-autoscaler                        | kube-system                   | Deployment | 1        |
        | ❌ | cluster-proportional-autoscaler-coredns   | kube-system                   | Deployment | 1        |
        | ❌ | coredns                                   | kube-system                   | Deployment | 2        |
        | ❌ | ebs-csi-controller                        | kube-system                   | Deployment | 2        |
        | ❌ | kube-state-metrics                        | kube-system                   | Deployment | 1        |
        | ❌ | opentelemetry-operator-controller-manager | opentelemetry-operator-system | Deployment | 1        |


    #### Check [[K8S003]](https://clowdhaus.github.io/eksup/info/checks/#k8s003)
        |   | NAME                                      | NAMESPACE                     | KIND       | SECONDS |
        |---|-------------------------------------------|-------------------------------|------------|---------|
        | ⚠️ | adot-collector                            | adot-collector-kubeprometheus | Deployment | 0       |
        | ⚠️ | cert-manager                              | cert-manager                  | Deployment | 0       |
        | ⚠️ | cert-manager-cainjector                   | cert-manager                  | Deployment | 0       |
        | ⚠️ | cert-manager-webhook                      | cert-manager                  | Deployment | 0       |
        | ⚠️ | knative-operator                          | default                       | Deployment | 0       |
        | ⚠️ | operator-webhook                          | default                       | Deployment | 0       |
        | ⚠️ | istio-ingressgateway                      | istio-system                  | Deployment | 0       |
        | ⚠️ | istiod                                    | istio-system                  | Deployment | 0       |
        | ⚠️ | karpenter                                 | karpenter                     | Deployment | 0       |
        | ⚠️ | hello-00001-deployment                    | knative-demo                  | Deployment | 0       |
        | ⚠️ | eventing-controller                       | knative-eventing              | Deployment | 0       |
        | ⚠️ | eventing-webhook                          | knative-eventing              | Deployment | 0       |
        | ⚠️ | imc-controller                            | knative-eventing              | Deployment | 0       |
        | ⚠️ | imc-dispatcher                            | knative-eventing              | Deployment | 0       |
        | ⚠️ | mt-broker-controller                      | knative-eventing              | Deployment | 0       |
        | ⚠️ | mt-broker-filter                          | knative-eventing              | Deployment | 0       |
        | ⚠️ | mt-broker-ingress                         | knative-eventing              | Deployment | 0       |
        | ⚠️ | pingsource-mt-adapter                     | knative-eventing              | Deployment | 0       |
        | ⚠️ | activator                                 | knative-serving               | Deployment | 0       |
        | ⚠️ | autoscaler                                | knative-serving               | Deployment | 0       |
        | ⚠️ | autoscaler-hpa                            | knative-serving               | Deployment | 0       |
        | ⚠️ | controller                                | knative-serving               | Deployment | 0       |
        | ⚠️ | domain-mapping                            | knative-serving               | Deployment | 0       |
        | ⚠️ | domainmapping-webhook                     | knative-serving               | Deployment | 0       |
        | ⚠️ | net-istio-controller                      | knative-serving               | Deployment | 0       |
        | ⚠️ | net-istio-webhook                         | knative-serving               | Deployment | 0       |
        | ⚠️ | webhook                                   | knative-serving               | Deployment | 0       |
        | ⚠️ | cluster-autoscaler                        | kube-system                   | Deployment | 0       |
        | ⚠️ | cluster-proportional-autoscaler-coredns   | kube-system                   | Deployment | 0       |
        | ⚠️ | coredns                                   | kube-system                   | Deployment | 0       |
        | ⚠️ | ebs-csi-controller                        | kube-system                   | Deployment | 0       |
        | ⚠️ | kube-state-metrics                        | kube-system                   | Deployment | 0       |
        | ⚠️ | opentelemetry-operator-controller-manager | opentelemetry-operator-system | Deployment | 0       |


    #### Check [[K8S004]](https://clowdhaus.github.io/eksup/info/checks/#k8s004)
    🚧 TODO

    #### Check [[K8S005]](https://clowdhaus.github.io/eksup/info/checks/#k8s005)
        |    | NAME                                      | NAMESPACE                     | KIND       | ANTIAFFINITY | TOPOLOGYSPREADCONSTRAINTS |
        |----|-------------------------------------------|-------------------------------|------------|--------------|---------------------------|
        | ❌ | adot-collector                            | adot-collector-kubeprometheus | Deployment | false        | false                     |
        | ❌ | cert-manager                              | cert-manager                  | Deployment | false        | false                     |
        | ❌ | cert-manager-cainjector                   | cert-manager                  | Deployment | false        | false                     |
        | ❌ | cert-manager-webhook                      | cert-manager                  | Deployment | false        | false                     |
        | ❌ | knative-operator                          | default                       | Deployment | false        | false                     |
        | ❌ | istiod                                    | istio-system                  | Deployment | false        | false                     |
        | ❌ | hello-00001-deployment                    | knative-demo                  | Deployment | false        | false                     |
        | ❌ | mt-broker-filter                          | knative-eventing              | Deployment | false        | false                     |
        | ❌ | mt-broker-ingress                         | knative-eventing              | Deployment | false        | false                     |
        | ❌ | activator                                 | knative-serving               | Deployment | false        | false                     |
        | ❌ | net-istio-controller                      | knative-serving               | Deployment | false        | false                     |
        | ❌ | net-istio-webhook                         | knative-serving               | Deployment | false        | false                     |
        | ❌ | cluster-autoscaler                        | kube-system                   | Deployment | false        | false                     |
        | ❌ | cluster-proportional-autoscaler-coredns   | kube-system                   | Deployment | false        | false                     |
        | ❌ | kube-state-metrics                        | kube-system                   | Deployment | false        | false                     |
        | ❌ | opentelemetry-operator-controller-manager | opentelemetry-operator-system | Deployment | false        | false                     |


    #### Check [[K8S006]](https://clowdhaus.github.io/eksup/info/checks/#k8s006)
        |    | NAME                                      | NAMESPACE                     | KIND       | READINESS PROBE |
        |----|-------------------------------------------|-------------------------------|------------|-----------------|
        | ❌ | adot-collector                            | adot-collector-kubeprometheus | Deployment | false           |
        | ❌ | cert-manager                              | cert-manager                  | Deployment | false           |
        | ❌ | cert-manager-cainjector                   | cert-manager                  | Deployment | false           |
        | ❌ | knative-operator                          | default                       | Deployment | false           |
        | ❌ | hello-00001-deployment                    | knative-demo                  | Deployment | false           |
        | ❌ | mt-broker-controller                      | knative-eventing              | Deployment | false           |
        | ❌ | pingsource-mt-adapter                     | knative-eventing              | Deployment | false           |
        | ❌ | autoscaler-hpa                            | knative-serving               | Deployment | false           |
        | ❌ | controller                                | knative-serving               | Deployment | false           |
        | ❌ | domain-mapping                            | knative-serving               | Deployment | false           |
        | ❌ | net-istio-controller                      | knative-serving               | Deployment | false           |
        | ❌ | net-istio-webhook                         | knative-serving               | Deployment | false           |
        | ❌ | cluster-autoscaler                        | kube-system                   | Deployment | false           |
        | ❌ | ebs-csi-controller                        | kube-system                   | Deployment | false           |
        | ❌ | opentelemetry-operator-controller-manager | opentelemetry-operator-system | Deployment | false           |


    #### Check [[K8S007]](https://clowdhaus.github.io/eksup/info/checks/#k8s007)
        ✅ - No StatefulSet workloads have a terminationGracePeriodSeconds set to more than 0

    #### Check [[K8S008]](https://clowdhaus.github.io/eksup/info/checks/#k8s008)
        |    | NAME     | NAMESPACE   | KIND      | DOCKERSOCKET |
        |----|----------|-------------|-----------|--------------|
        | ❌ | aws-node | kube-system | DaemonSet | true         |


    #### Check [[K8S009]](https://clowdhaus.github.io/eksup/info/checks/#k8s009)
        |    | NAME                     | NAMESPACE | KIND              |
        |----|--------------------------|-----------|-------------------|
        | ❌ | eks.privileged           |           | PodSecurityPolicy |
        | ❌ | prometheus-node-exporter |           | PodSecurityPolicy |


    #### Check [[K8S0011]](https://clowdhaus.github.io/eksup/info/checks/#k8s011)
        ✅ - `kube-proxy` version is aligned with the node/`kubelet` versions in use

2. Inspect [AWS service quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html) before upgrading. Accounts that are multi-tenant or already have a number of resources provisioned may be at risk of hitting service quota limits which will cause the cluster upgrade to fail, or impede the upgrade process.

3. Verify that there is sufficient IP space available to the pods running in the cluster when using custom networking. With the in-place, surge upgrade process, there will be higher IP consumption during the upgrade.

    <details>
    <summary>📌 CLI Example</summary>

    Ensure you have updated your `kubeconfig` locally before executing the following commands:

    ```sh
    aws eks update-kubeconfig --region us-east-1  --name mulesoft-obs-demo
    ```

    Get the number of available IPs in each subnet used by the custom networking `ENIConfig` resources:
    ```sh
    aws ec2 describe-subnets --region us-east-1 --subnet-ids \
        $(kubectl get ENIConfigs -n kube-system -o jsonpath='{.items[*].spec.subnet}') \
        --query 'Subnets[*].AvailableIpAddressCount'
    ```

    </details>

    #### Check [[AWS002]](https://clowdhaus.github.io/eksup/info/checks/#aws002)
        ✅ - There is sufficient IP space in the subnets provided

#### EKS Managed Nodegroup

ℹ️ [Updating a managed nodegroup](https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html)

ℹ️ [Managed nodegroup update behavior](https://docs.aws.amazon.com/eks/latest/userguide/managed-node-update-behavior.html)

The [nodegroup update config](https://docs.aws.amazon.com/eks/latest/APIReference/API_NodegroupUpdateConfig.html) supports updating multiple nodes, up to a max of 100 nodes, in parallel during an upgrade. It is recommended to start with an update configuration of 30% max unavailable percentage and adjust as necessary. Increasing this percentage will reduce the time to upgrade (until the max quota of 100 nodes is reached) but also increase the amount of churn within then nodegroup and therefore increasing the potential for disruption to services running on the nodes. Conversely, reducing the percentage will increase the time to upgrade but also reduce the amount of churn within the nodegroup and therefore reduce the potential for disruption to services running on the nodes. Users should test the impact of the update configuration on their workloads and adjust as necessary to balance between time to upgrade and potential risk for service disruption.

The default update strategy for EKS managed nodegroups is a surge, rolling update which respects the pod disruption budgets for your cluster. Updates can fail if there's a pod disruption budget issue that prevents Amazon EKS from gracefully draining the pods that are running on the nodegroup, or if pods do not safely evict from the nodes within a 15 minute window after the node has been marked as cordoned and set to drain. To circumvent this, you can specify a force update which does *NOT* respect pod disruption budgets. Updates occur regardless of pod disruption budget issues by forcing node replacements.

##### Pre-Upgrade

1. Ensure the EKS managed nodegroup(s) are free of any health issues as reported by Amazon EKS. If there are any issues, resolution of those issues is required before upgrading the cluster.

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    aws eks describe-nodegroup --region us-east-1 --cluster-name mulesoft-obs-demo \
      --nodegroup-name <NAME> --query 'nodegroup.health'
    ```

    </details>

    #### Check [[EKS003]](https://clowdhaus.github.io/eksup/info/checks/#eks003)
        ✅ - There are no reported nodegroup health issues.

2. Ensure the EKS managed nodegroup(s) do not have any pending updates and they are using the latest version of their respective launch templates. If the nodegroup(s) are not using the latest launch template, it is recommended to update to the latest to avoid accidentally introducing any additional and un-intended changes during the upgrade.

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    // TODO
    ```

    </details>

    Check [[EKS006]](https://clowdhaus.github.io/eksup/info/checks/#eks006)
        ✅ - There are no pending updates for the EKS managed nodegroup(s)

##### Upgrade

The following steps are applicable for each nodegroup in the cluster.

Custom AMI:

  1. Update the launch template, specifying the ID of an AMI that matches the control plane's Kubernetes version:

      ```sh
      aws ec2 create-launch-template-version --region us-east-1 \
        --launch-template-id <LAUNCH_TEMPLATE_ID> \
        --source-version <LAUNCH_TEMPLATE_VERSION> --launch-template-data 'ImageId=<AMI_ID>'
      ```

  2. Update the launch template version specified on the EKS managed nodegroup:

      ```sh
      aws eks update-nodegroup-version --region us-east-1 --cluster-name mulesoft-obs-demo \
        --nodegroup-name <NODEGROUP_NAME> --launch-template <LAUNCH_TEMPLATE>
      ```


EKS optimized AMI provided by Amazon EKS:

  1. Update the Kubernetes version specified on the EKS managed nodegroup:

      ```sh
      aws eks update-nodegroup-version --region us-east-1 --cluster-name mulesoft-obs-demo \
        --nodegroup-name <NODEGROUP_NAME> --kubernetes-version 1.25
      ```

##### Process

The following events take place when a nodegroup detects changes that require nodes to be cycled and replaced, such as upgrading the Kubernetes version or deploying a new AMI:

For each node in the nodegroup:
  - The node is cordoned so that Kubernetes does not schedule new Pods on it.
  - The node is then drained while respecting the set `PodDisruptionBudget` and `GracefulTerminationPeriod` settings for pods for up to 15 minutes.
  - The control plane reschedules Pods managed by controllers onto other nodes. Pods that cannot be rescheduled stay in the Pending phase until they can be rescheduled.

The node pool upgrade process may take up to a few hours depending on the upgrade strategy, the number of nodes, and their workload configurations. Configurations that can cause a node upgrade to take longer to complete include:

  - A high value of `terminationGracePeriodSeconds` in a Pod's configuration.
  - A conservative Pod Disruption Budget.
  - Node affinity interactions
  - Attached PersistentVolumes

In the event that you encounter pod disruption budget issues or update timeouts due to pods not safely evicting from the nodes within the 15 minute window, you can force the update to proceed by adding the `--force` flag.


## Upgrade EKS Addons

### Addon Pre-Upgrade

1. Ensure the EKS addons in use are free of any health issues as reported by Amazon EKS. If there are any issues, resolution of those issues is required before upgrading the cluster.

    <details>
    <summary>📌 CLI Example</summary>

    ```sh
    aws eks describe-addon --region us-east-1 --cluster-name mulesoft-obs-demo \
        --addon-name <ADDON_NAME> --query 'addon.health'
    ```

    </details>

    #### Check [[EKS004]](https://clowdhaus.github.io/eksup/info/checks/#eks004)
        ✅ - There are no reported addon health issues.

### Addon Upgrade

1. Upgrade the addon to an appropriate version for the upgraded Kubernetes version:

    ```sh
    aws eks update-addon --region us-east-1 --cluster-name mulesoft-obs-demo \
        --addon-name <ADDON_NAME> --addon-version <ADDON_VERSION>
    ```

    You may need to add `--resolve-conflicts OVERWRITE` to the command if the addon has been modified since it was deployed to ensure the addon is upgraded.

## Post Upgrade

- Update applications running on the cluster
- Update tools that interact with the cluster (kubectl, awscli, etc.)
