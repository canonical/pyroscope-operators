Feature: ingress

  Scenario: Ingress follower
    Given a follower unit in a happy state, with ingress
    When we process an update-status event
    Then the state is still happy
    And we haven't published ingress details in this unit's databags