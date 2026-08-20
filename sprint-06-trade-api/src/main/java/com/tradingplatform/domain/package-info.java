/**
 * The Sprint 5 domain, moved in as source: entities, enumerations, the order request DTO, the
 * exception hierarchy and business rules 1 to 8.
 *
 * <p>Copy your Sprint 5 sources in here, keeping the package name they already have, and copy the
 * tests beside the tests you write this week. Nothing resolves this code as an artefact and there
 * is no {@code mvn install} step: it is compiled by this project's build, which is what lets a
 * fresh checkout build the service with one command.
 *
 * <p>This package sits beside the service packages rather than underneath them, because it depends
 * on none of them and they all depend on it. Nothing here knows that HTTP, MyBatis or Spring
 * exists. Bean Validation annotations are the one exception the architecture allows, because they
 * are declarations rather than behaviour.
 *
 * <p>The constraint used to be enforced by a separate Maven module and is now a rule about what may
 * appear inside a package. A servlet, Spring or MyBatis type in here fails the layering criterion,
 * and nothing but the review will tell you it is there.
 */
package com.tradingplatform.domain;
