/* eslint-disable */
// rename this file from _test_[name] to test_[name] to activate
// and remove above this line

QUnit.test("test: Past Serial No", function (assert) {
	let done = assert.async();

	// number of asserts
	assert.expect(1);

	frappe.run_serially([
		// insert a new Past Serial No
		() => frappe.tests.make('Past Serial No', [
			// values to be set
			{key: 'value'}
		]),
		() => {
			// nosemgrep: frappe-semgrep-rules.rules.frappe-cur-frm-usage
			assert.equal(cur_frm.doc.key, 'value');
		},
		() => done()
	]);

});
