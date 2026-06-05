import api from './index'

// ── 认证 ──────────────────────────────────────────────────
export function loginAPI(data) {
  return api.post('/auth/login', data)
}

export function registerAPI(data) {
  return api.post('/auth/register', data)
}

// ── 顾客 ──────────────────────────────────────────────────
export function listMerchantsAPI() {
  return api.get('/customer/merchants')
}

export function listDishesAPI(merchantId) {
  return api.get('/customer/dishes', { params: merchantId ? { merchant_id: merchantId } : {} })
}

export function listAddressesAPI() {
  return api.get('/customer/addresses')
}

export function addAddressAPI(data) {
  return api.post('/customer/addresses', data)
}

export function deleteAddressAPI(id) {
  return api.delete(`/customer/addresses/${id}`)
}

export function placeOrderAPI(data) {
  return api.post('/customer/order', data)
}

export function listCustomerOrdersAPI() {
  return api.get('/customer/orders')
}

export function cancelOrderAPI(id) {
  return api.put(`/customer/order/${id}/cancel`)
}

// ── 商家 ──────────────────────────────────────────────────
export function listMerchantDishesAPI() {
  return api.get('/merchant/dishes')
}

export function addDishAPI(data) {
  return api.post('/merchant/dishes', data)
}

export function updateDishAPI(id, data) {
  return api.put(`/merchant/dishes/${id}`, data)
}

export function deleteDishAPI(id) {
  return api.delete(`/merchant/dishes/${id}`)
}

export function listMerchantOrdersAPI() {
  return api.get('/merchant/orders')
}

export function acceptOrderAPI(id) {
  return api.put(`/merchant/order/${id}/accept`)
}

export function rejectOrderAPI(id) {
  return api.put(`/merchant/order/${id}/reject`)
}

export function assignCourierAPI(orderId, courierId) {
  return api.put(`/merchant/order/${orderId}/assign`, { courier_id: courierId })
}

export function listAvailableCouriersAPI() {
  return api.get('/merchant/available-couriers')
}

// ── 骑手 ──────────────────────────────────────────────────
export function listAvailableOrdersAPI() {
  return api.get('/courier/available-orders')
}

export function pickupOrderAPI(id) {
  return api.put(`/courier/order/${id}/pickup`)
}

export function listCourierOrdersAPI() {
  return api.get('/courier/orders')
}

export function deliverOrderAPI(id) {
  return api.put(`/courier/order/${id}/deliver`)
}
