// Run with node vmmsx/tests/test_approval_presentation.cjs.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const context = {
 __: text => text,
 frappe: {ui: {form: {on() {}}},
  datetime: {str_to_user: value => value},
  utils: {escape_html: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')}}
};
vm.createContext(context);
for (const file of ['vmms_volunteer/doctype/vmms_volunteer/vmms_volunteer.js', 'vmms_member/doctype/vmms_member/vmms_member.js']) {
 vm.runInContext(fs.readFileSync(path.join(__dirname, '..', file), 'utf8'), context);
}
const empty = vm.runInContext(`vmmsx_volunteer.verification_html({application: {
 application: 'A1', approval_state: 'Approved', applied_on: '2018-01-01', decisions: []
}})`, context);
assert.match(empty, /Approved/);
assert.match(empty, /No approval decision details are recorded/);
assert.doesNotMatch(empty, /no approver acted|Administrator|onerc_vmms|migration/i);
const members = vm.runInContext('vmmsx_member.history_html({history: []})', context);
assert.match(members, /No approval decision details are recorded/);
const genuine = vm.runInContext(`vmmsx_volunteer.verification_html({application: {
 application: 'A1', approval_state: 'Approved', decisions: [{stage_label: 'County review',
 approver: 'coordinator@example.test', decision: 'Approved', decided_on: '2018-01-01', reason: 'Documents reviewed.'}]
}})`, context);
assert.match(genuine, /coordinator@example.test/);
assert.match(genuine, /County review/);
assert.match(genuine, /Documents reviewed/);
console.log('PASS: source status remains visible; absent decision details do not imply nobody approved; genuine history remains visible.');
