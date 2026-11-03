Feature: pyroscope

  Scenario Outline: Pyroscope config is generated for different URLs
    Given the Pyroscope URL is "<url>"
    When the Pyroscope config is generated
    Then a configuration output is returned

    Examples:
      | url     |
      | /       |
      | None    |
      | foo.com |

  Scenario: Reporting enabled by default omits the analytics section
    Given reporting_enabled is true by default
    When the Pyroscope config is generated
    Then the config has no analytics section

  Scenario: Reporting disabled adds analytics.reporting_enabled
    Given reporting_enabled is false
    When the Pyroscope config is generated
    Then analytics.reporting_enabled is false