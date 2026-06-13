import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const read = (path) => readFile(new URL(path, import.meta.url), 'utf8')

test('API service layer exposes every documented business operation', async () => {
  const source = await read('../src/api/services.js')
  const expected = [
    'loginAPI',
    'registerAPI',
    'listMerchantsAPI',
    'listDishesAPI',
    'listAddressesAPI',
    'addAddressAPI',
    'deleteAddressAPI',
    'placeOrderAPI',
    'listCustomerOrdersAPI',
    'cancelOrderAPI',
    'listMerchantDishesAPI',
    'addDishAPI',
    'updateDishAPI',
    'deleteDishAPI',
    'listMerchantOrdersAPI',
    'acceptOrderAPI',
    'rejectOrderAPI',
    'assignCourierAPI',
    'listAvailableCouriersAPI',
    'listAvailableOrdersAPI',
    'pickupOrderAPI',
    'listCourierOrdersAPI',
    'deliverOrderAPI',
  ]

  for (const operation of expected) {
    assert.match(source, new RegExp(`export function ${operation}\\(`))
  }
})

test('router protects all three role workspaces', async () => {
  const source = await read('../src/router/index.js')
  for (const role of ['customer', 'merchant', 'courier']) {
    assert.match(source, new RegExp(`path: '/${role}'[\\s\\S]*meta: \\{ role: '${role}' \\}`))
  }
  assert.match(source, /if \(!auth\.token\)/)
  assert.match(source, /if \(auth\.role !== to\.meta\.role\)/)
})

test('auth store persists and clears the full authentication context', async () => {
  const source = await read('../src/stores/auth.js')
  for (const key of ['token', 'role', 'userId', 'userName']) {
    assert.match(source, new RegExp(`localStorage\\.setItem\\('${key}'`))
    assert.match(source, new RegExp(`localStorage\\.removeItem\\('${key}'\\)`))
  }
})

test('HTTP client attaches bearer token and handles expired sessions', async () => {
  const source = await read('../src/api/index.js')
  assert.match(source, /Authorization = `Bearer \$\{auth\.token\}`/)
  assert.match(source, /if \(status === 401\)/)
  assert.match(source, /auth\.logout\(\)/)
})
