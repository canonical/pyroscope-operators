Feature: peers

  Scenario Outline: get_fqdns aggregates this unit and peer FQDNs
    Given the peer relation provides FQDNs <peer_fqdns>
    When get_fqdns is called
    Then the result contains this unit's own FQDN and every peer FQDN

    Examples:
      | peer_fqdns                  |
      | ["matterhost", "localmost"] |
      | ["matter.host"]             |
      | []                          |
      | no peer relation            |