Feature: charm-statuses

  Scenario Outline: Worker status reflects the Kubernetes patch result
    Given the k8s service patch reports status "<status>"
    When the charm reconciles
    Then the unit status equals "<status>"

    Examples:
      | status                                  |
      | blocked "`juju trust` this application" |
      | waiting ""                              |