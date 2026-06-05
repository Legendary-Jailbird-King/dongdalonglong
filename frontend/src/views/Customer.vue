<template>
  <div class="customer-app">
    <header class="app-header">
      <div class="header-brand">
        <span class="brand-icon">🍔</span>
        <h2>外卖点餐</h2>
      </div>
      <div class="header-right">
        <span class="user-name">👤 {{ auth.userName }}</span>
        <el-button size="small" round @click="handleLogout">退出</el-button>
      </div>
    </header>

    <div class="main-container">
      <el-tabs v-model="activeTab" class="main-tabs">

        <!-- ── 选择商家 ── -->
        <el-tab-pane label="🏪 商家" name="merchant">
          <p class="section-desc">请先选择一家商家进入店铺点餐</p>
          <div class="merchant-grid">
            <div
              v-for="m in merchants"
              :key="m.id"
              class="merchant-card"
              @click="enterMerchant(m)"
            >
              <span class="merchant-icon">🏪</span>
              <p class="merchant-name">{{ m.name || '商家 #' + m.id }}</p>
              <p class="merchant-dish-count">{{ m.dish_count }} 个菜品</p>
            </div>
            <el-empty v-if="merchants.length === 0" description="暂无商家" />
          </div>
        </el-tab-pane>

        <!-- ── 浏览菜单 ── -->
        <el-tab-pane :label="'📋 ' + (currentMerchantName || '菜单')" name="menu" :disabled="!currentMerchantId">
          <!-- 当前商家信息 -->
          <div class="current-merchant-bar">
            <span class="merchant-label">🏪 {{ currentMerchantName }}</span>
            <el-button size="small" type="info" plain round @click="leaveMerchant">切换商家</el-button>
          </div>

          <div class="filter-bar">
            <el-badge :value="cart.length" :hidden="cart.length === 0" class="cart-badge">
              <el-button size="small" type="warning" @click="activeTab='cart'">🛒 购物车</el-button>
            </el-badge>
          </div>

          <div class="dish-list">
            <div v-for="d in dishes" :key="d.id" class="dish-card" @click="addToCart(d)">
              <div class="dish-left">
                <span class="dish-emoji">🍽️</span>
                <div>
                  <p class="dish-name">{{ d.name }}</p>
                  <p class="dish-price-sm">¥{{ Number(d.price).toFixed(2) }}</p>
                </div>
              </div>
              <span class="add-btn">+</span>
            </div>
            <el-empty v-if="dishes.length === 0" description="该商家暂无菜品" />
          </div>
        </el-tab-pane>

        <!-- ── 购物车 ── -->
        <el-tab-pane :label="'🛒 购物车 (' + cart.length + ')'" name="cart" :disabled="!currentMerchantId">
          <div class="current-merchant-bar small">
            <span>🏪 {{ currentMerchantName }}</span>
          </div>

          <div v-if="cart.length === 0" class="empty-state">
            <span class="empty-icon">🛒</span>
            <p>购物车是空的</p>
            <el-button type="primary" @click="activeTab='menu'">去菜单逛逛</el-button>
          </div>
          <div v-else>
            <div v-for="(item, idx) in cart" :key="idx" class="cart-item">
              <span class="cart-name">{{ item.name }}</span>
              <span class="cart-price">¥{{ Number(item.price).toFixed(2) }}</span>
              <el-input-number v-model="item.quantity" :min="1" :max="99" size="small" />
              <el-button size="small" circle @click="cart.splice(idx, 1)">✕</el-button>
            </div>
            <div class="cart-footer">
              <span class="cart-total">合计 ¥{{ cartTotal.toFixed(2) }}</span>
              <el-button type="primary" size="large" round @click="showPlaceOrder = true" :disabled="cart.length === 0">
                去下单
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ── 地址簿 ── -->
        <el-tab-pane label="📍 地址" name="address">
          <el-button type="primary" size="small" style="margin-bottom:12px" @click="showAddAddress = true">+ 添加地址</el-button>
          <div v-for="a in addresses" :key="a.id" class="address-card">
            <div>
              <p class="addr-phone">📞 {{ a.phone }}</p>
              <p class="addr-text">📍 {{ a.address }}</p>
            </div>
            <el-button size="small" type="danger" text @click="handleDeleteAddress(a.id)">删除</el-button>
          </div>
          <el-empty v-if="addresses.length === 0" description="暂无地址" />
        </el-tab-pane>

        <!-- ── 我的订单 ── -->
        <el-tab-pane label="📦 订单" name="orders">
          <el-button size="small" style="margin-bottom:12px" @click="loadOrders">刷新</el-button>
          <div v-for="o in orders" :key="o.id" class="order-card" :class="'s-' + o.status">
            <div class="order-head">
              <span class="order-id">#{{ o.id }}</span>
              <el-tag :type="statusTag(o.status)" size="small" effect="dark">{{ o.status_text }}</el-tag>
            </div>
            <p class="order-dishes">{{ o.dish_summary }}</p>
            <div class="order-meta">
              <span>🏪 {{ o.merchant_name || '商家 #' + o.merchant_id }}</span>
              <span class="order-total">¥{{ Number(o.total).toFixed(2) }}</span>
              <span>{{ formatTime(o.order_time) }}</span>
            </div>
            <el-button
              v-if="o.status === 0" size="small" type="danger" round
              style="margin-top:8px" @click="handleCancelOrder(o.id)"
            >取消订单</el-button>
          </div>
          <el-empty v-if="orders.length === 0" description="暂无订单" />
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 下单弹窗 -->
    <el-dialog v-model="showPlaceOrder" title="确认下单" width="380px" class="order-dialog">
      <div class="order-merchant-info">
        🏪 <b>{{ currentMerchantName }}</b>
      </div>
      <el-form label-position="top">
        <el-form-item label="收货地址">
          <el-select v-model="orderForm.shipping_id" placeholder="选择地址" style="width:100%">
            <el-option v-for="a in addresses" :key="a.id" :value="a.id" :label="a.address+' ('+a.phone+')'" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="cart-review">
        <p v-for="i in cart" :key="i.dish_id">• {{ i.name }} x{{ i.quantity }} — ¥{{ (Number(i.price)*i.quantity).toFixed(2) }}</p>
      </div>
      <template #footer>
        <el-button @click="showPlaceOrder = false" round>取消</el-button>
        <el-button type="primary" :loading="placing" round @click="handlePlaceOrder">
          确认 ¥{{ cartTotal.toFixed(2) }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 地址弹窗 -->
    <el-dialog v-model="showAddAddress" title="添加地址" width="360px" class="addr-dialog">
      <el-form label-position="top">
        <el-form-item label="电话"><el-input v-model="addrForm.phone" placeholder="手机号" /></el-form-item>
        <el-form-item label="地址"><el-input v-model="addrForm.address" placeholder="详细地址" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddAddress = false" round>取消</el-button>
        <el-button type="primary" @click="handleAddAddress" round>确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  listMerchantsAPI, listDishesAPI, listAddressesAPI, addAddressAPI, deleteAddressAPI,
  placeOrderAPI, listCustomerOrdersAPI, cancelOrderAPI,
} from '../api/services'

const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('merchant')
const dishes = ref([])
const merchants = ref([])
const currentMerchantId = ref(null)
const currentMerchantName = ref('')
const cart = ref([])
const addresses = ref([])
const orders = ref([])
const showPlaceOrder = ref(false)
const showAddAddress = ref(false)
const placing = ref(false)

const orderForm = reactive({ shipping_id: null })
const addrForm = reactive({ phone: '', address: '' })

const cartTotal = computed(() => cart.value.reduce((s, i) => s + Number(i.price) * i.quantity, 0))

function statusTag(s) { return { 0: 'warning', 1: '', 2: '', 3: 'success', 4: 'info', 5: 'danger' }[s] || 'info' }
function formatTime(t) { return t ? new Date(t).toLocaleString('zh-CN') : '' }

function enterMerchant(m) {
  // 切换商家时清空购物车
  if (currentMerchantId.value && currentMerchantId.value !== m.id && cart.value.length > 0) {
    ElMessage.warning('已切换商家，购物车已清空')
  }
  currentMerchantId.value = m.id
  currentMerchantName.value = m.name || '商家 #' + m.id
  cart.value = []
  loadDishes()
  activeTab.value = 'menu'
}

function leaveMerchant() {
  if (cart.value.length > 0) {
    ElMessageBox.confirm('切换商家将清空当前购物车，确定？', '提示', {
      confirmButtonText: '确定切换',
      type: 'warning',
    }).then(() => {
      currentMerchantId.value = null
      currentMerchantName.value = ''
      cart.value = []
      activeTab.value = 'merchant'
    }).catch(() => {})
  } else {
    currentMerchantId.value = null
    currentMerchantName.value = ''
    activeTab.value = 'merchant'
  }
}

function addToCart(d) {
  const ex = cart.value.find(i => i.dish_id === d.id)
  ex ? ex.quantity++ : cart.value.push({ dish_id: d.id, name: d.name, price: d.price, merchant_id: d.merchant_id, quantity: 1 })
  ElMessage.success(`已添加「${d.name}」`)
}

async function loadDishes() {
  if (!currentMerchantId.value) return
  try { const r = await listDishesAPI(currentMerchantId.value); dishes.value = r.data || [] } catch { /* */ }
}

async function loadMerchants() {
  try { const r = await listMerchantsAPI(); merchants.value = r.data || [] } catch { /* */ }
}

async function loadAddresses() {
  try { const r = await listAddressesAPI(); addresses.value = r.data || [] } catch { /* */ }
}

async function loadOrders() {
  try { const r = await listCustomerOrdersAPI(); orders.value = r.data || [] } catch { /* */ }
}

async function handleAddAddress() {
  if (!addrForm.phone || !addrForm.address) { ElMessage.warning('请填写完整'); return }
  try { await addAddressAPI({ ...addrForm }); ElMessage.success('已添加'); showAddAddress.value = false; addrForm.phone = ''; addrForm.address = ''; await loadAddresses() } catch { /* */ }
}

async function handleDeleteAddress(id) {
  try { await ElMessageBox.confirm('确定删除？', '提示', { type: 'warning' }); await deleteAddressAPI(id); ElMessage.success('已删除'); await loadAddresses() } catch { /* */ }
}

async function handlePlaceOrder() {
  if (!cart.value.length) { ElMessage.warning('购物车为空'); return }
  if (!orderForm.shipping_id) { ElMessage.warning('请选择地址'); return }
  placing.value = true
  try {
    await placeOrderAPI({
      merchant_id: currentMerchantId.value,
      shipping_id: orderForm.shipping_id,
      dishes: cart.value.map(i => ({ dish_id: i.dish_id, quantity: i.quantity }))
    })
    ElMessage.success('下单成功！')
    cart.value = []
    showPlaceOrder.value = false
    activeTab.value = 'orders'
    await loadOrders()
  } catch { /* */ } finally { placing.value = false }
}

async function handleCancelOrder(id) {
  try { await ElMessageBox.confirm('确定取消？', '提示', { type: 'warning' }); await cancelOrderAPI(id); ElMessage.success('已取消'); await loadOrders() } catch { /* */ }
}

function handleLogout() { auth.logout(); router.push('/') }

watch(activeTab, (v) => {
  if (v === 'merchant') loadMerchants()
  if (v === 'menu') loadDishes()
  if (v === 'address') loadAddresses()
  if (v === 'orders') loadOrders()
})

onMounted(() => { loadMerchants(); loadAddresses(); loadOrders() })
</script>

<style scoped>
.customer-app {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f4ff 0%, #f5f7fa 100%);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 12px 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-brand { display: flex; align-items: center; gap: 8px; }
.header-brand h2 { font-size: 17px; color: #1a1a2e; }
.brand-icon { font-size: 22px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { color: #666; font-size: 13px; }

.main-container {
  max-width: 560px;
  margin: 12px auto;
  padding: 0 12px;
}
.main-tabs {
  background: #fff;
  border-radius: 16px;
  padding: 4px 14px 14px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.section-desc { color: #999; font-size: 13px; margin-bottom: 12px; }

/* ── 商家选择 ── */
.merchant-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.merchant-card {
  background: #fafbfc;
  border: 2px solid #f0f0f0;
  border-radius: 14px;
  padding: 24px 16px;
  text-align: center;
  cursor: pointer;
  transition: all 0.25s;
}
.merchant-card:hover {
  border-color: #667eea;
  background: #f5f5ff;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102,126,234,0.15);
}
.merchant-icon { font-size: 36px; display: block; margin-bottom: 8px; }
.merchant-name { font-weight: 700; font-size: 15px; color: #1a1a2e; margin-bottom: 4px; }
.merchant-dish-count { font-size: 12px; color: #999; }

/* ── 当前商家信息 ── */
.current-merchant-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #667eea10, #764ba210);
  border: 1px solid #667eea30;
  border-radius: 10px;
  padding: 10px 14px;
  margin-bottom: 10px;
}
.current-merchant-bar.small { margin-top: 4px; }
.merchant-label { font-weight: 600; color: #667eea; }

.filter-bar { display: flex; gap: 8px; margin-bottom: 8px; align-items: center; }
.cart-badge :deep(.el-badge__content) { background: #f56c6c; }

/* ── 菜品列表 ── */
.dish-list { display: flex; flex-direction: column; gap: 6px; }
.dish-card {
  display: flex; justify-content: space-between; align-items: center;
  background: #fafbfc; border: 1px solid #f0f0f0; border-radius: 12px;
  padding: 14px 16px; cursor: pointer; transition: all 0.2s;
}
.dish-card:hover { background: #f5f5ff; border-color: #d0d0f0; }
.dish-left { display: flex; align-items: center; gap: 10px; }
.dish-emoji { font-size: 28px; }
.dish-name { font-weight: 600; color: #1a1a2e; font-size: 15px; }
.dish-price-sm { font-size: 13px; color: #f56c6c; font-weight: 600; margin-top: 2px; }
.dish-right { display: flex; align-items: center; gap: 12px; }
.dish-price { color: #f56c6c; font-weight: 700; font-size: 15px; }
.add-btn {
  width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #667eea, #764ba2); color: #fff;
  border-radius: 50%; font-size: 18px; font-weight: 700; flex-shrink: 0;
}

/* ── 购物车 ── */
.empty-state { text-align: center; padding: 40px 0; color: #999; }
.empty-icon { font-size: 40px; display: block; margin-bottom: 10px; }
.cart-item { display: flex; align-items: center; gap: 10px; padding: 10px 0; border-bottom: 1px solid #f5f5f5; }
.cart-name { flex: 1; font-weight: 500; }
.cart-price { color: #f56c6c; font-weight: 600; min-width: 60px; }
.cart-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 14px; }
.cart-total { font-size: 20px; font-weight: 700; color: #f56c6c; }
.cart-review { background: #f8f9fc; border-radius: 10px; padding: 12px; margin-top: 8px; }
.cart-review p { line-height: 1.8; color: #555; font-size: 13px; }

.order-merchant-info {
  background: linear-gradient(135deg, #667eea15, #764ba215);
  padding: 10px 14px;
  border-radius: 10px;
  margin-bottom: 12px;
  font-size: 14px;
}

/* ── 地址 ── */
.address-card {
  display: flex; justify-content: space-between; align-items: center;
  background: #fafbfc; border: 1px solid #f0f0f0; border-radius: 12px;
  padding: 14px 16px; margin-bottom: 8px;
}
.addr-phone { font-weight: 600; color: #1a1a2e; margin-bottom: 2px; }
.addr-text { color: #777; font-size: 13px; }

/* ── 订单 ── */
.order-card {
  background: #fff; border: 1px solid #f0f0f0; border-radius: 14px;
  padding: 14px 16px; margin-bottom: 10px; border-left: 4px solid #ddd;
}
.order-card.s-0 { border-left-color: #e6a23c; }
.order-card.s-1 { border-left-color: #409eff; }
.order-card.s-2 { border-left-color: #67c23a; }
.order-card.s-3 { border-left-color: #67c23a; }
.order-card.s-4 { border-left-color: #999; }
.order-card.s-5 { border-left-color: #f56c6c; }
.order-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.order-id { font-weight: 700; }
.order-dishes { color: #555; font-size: 13px; margin-bottom: 6px; }
.order-meta { display: flex; gap: 14px; font-size: 11px; color: #aaa; }
.order-total { color: #f56c6c; font-weight: 600; }

.order-dialog :deep(.el-dialog), .addr-dialog :deep(.el-dialog) { border-radius: 16px; }
</style>
