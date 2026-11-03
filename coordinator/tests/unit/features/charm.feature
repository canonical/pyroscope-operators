Feature: charm

  Scenario Outline: Coordinator starts with and without leadership
    Given a coordinator unit with an S3 relation and the required containers
    And the unit is "<leadership>"
    When the start event is handled
    Then the charm runs without raising an exception

    Examples:
      | leadership |
      | leader     |
      | non-leader |