Feature: coherence

  Scenario Outline: Coordinator judges whether the deployed role set is coherent
    Given workers report roles "<roles>"
    When coherency is evaluated against the minimal deployment
    Then the deployment is considered "<coherent>"

    Examples:
      | roles                                    | coherent   |
      | query-backend only                       | incoherent |
      | distributor only                         | incoherent |
      | distributor + segment-writer             | incoherent |
      | the exact MINIMAL_DEPLOYMENT role set    | coherent   |