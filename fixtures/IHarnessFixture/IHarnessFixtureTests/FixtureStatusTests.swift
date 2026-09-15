import XCTest
@testable import IHarnessFixture

final class FixtureStatusTests: XCTestCase {
    func testApprovedReadyCopy() {
        XCTAssertEqual(FixtureStatus.ready, "iHarness fixture ready")
        XCTAssertEqual(FixtureStatus.detail, "Build, test, install, and launch completed.")
    }
}
