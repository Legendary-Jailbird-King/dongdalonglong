<template>
  <div class="courier-app">
    <header class="app-header">
      <div class="header-brand">
        <span class="brand-icon">🛵</span>
        <h2>骑手控制台</h2>
      </div>
      <div class="header-right">
        <el-tag :type="courierBusy ? 'danger' : 'success'" size="small" effect="dark">
          {{ courierBusy ? '忙碌' : '空闲' }}
        </el-tag>
        <span class="user-name">{{ auth.userName }}</span>
        <el-button size="small" round @click="handleLogout">退出</el-button>
      </div>
    </header>

    <div class="main-container">
      <el-tabs v-model="activeTab" class="main-tabs">
        <!-- ── 可抢订单 ── -->
        <el-tab-pane label="📋 可抢订单" name="available">
          <div class="toolbar">
            <span class="hint">商家已接单、等待骑手配送的订单</span>
            <el-button size="small" type="primary" @click="loadAvailableOrders">刷新</el-button>
          </div>

          <div v-if="availableOrders.length === 0" class="empty-state">
            <span class="empty-icon">📭</span>
            <p>暂无待抢订单</p>
          </div>

          <div v-for="o in availableOrders" :key="o.id" class="order-card pickup-card">
            <div class="card-badge">待抢</div>
            <div class="order-header">
              <span class="order-id">#{{ o.id }}</span>
              <span class="order-time">{{ formatTime(o.order_time) }}</span>
            </div>
            <p class="order-dishes">{{ o.dish_summary }}</p>
            <div class="order-info-row">
              <span>📍 {{ o.shipping_address }}</span>
              <span>📞 {{ o.shipping_phone }}</span>
            </div>
            <div class="order-footer">
              <span class="order-total">¥{{ Number(o.total).toFixed(2) }}</span>
              <el-button type="primary" size="large" round @click="handlePickup(o.id)">
                🏃 抢单
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- ── 我的订单 ── -->
        <el-tab-pane label="📦 我的派送" name="mine">
          <div class="toolbar">
            <span class="hint">已接单的配送任务</span>
            <el-button size="small" @click="loadMyOrders">刷新</el-button>
          </div>

          <div v-if="myOrders.length === 0" class="empty-state">
            <span class="empty-icon">🛵</span>
            <p>暂无派送任务</p>
          </div>

          <div v-for="o in myOrders" :key="o.id" class="order-card" :class="'status-' + o.status">
            <div class="order-header">
              <span class="order-id">#{{ o.id }}</span>
              <el-tag :type="statusTag(o.status)" size="small" effect="dark">
                {{ o.status_text }}
              </el-tag>
            </div>
            <p class="order-dishes">{{ o.dish_summary }}</p>
            <div class="order-info-row">
              <span>📍 {{ o.shipping_address }}</span>
              <span>📞 {{ o.shipping_phone }}</span>
            </div>
            <div class="order-footer">
              <span class="order-total">¥{{ Number(o.total).toFixed(2) }}</span>
              <el-button
                v-if="o.status === 2"
                type="success"
                size="large"
                round
                @click="handleDeliver(o.id)"
              >
                ✅ 确认送达
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  listAvailableOrdersAPI, pickupOrderAPI,
  listCourierOrdersAPI, deliverOrderAPI,
} from '../api/services'

const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('available')
const availableOrders = ref([])
const myOrders = ref([])
let ws = null

const courierBusy = computed(() => myOrders.value.some(o => o.status === 2))

function statusTag(s) {
  return { 0: 'warning', 1: 'primary', 2: '', 3: 'success', 4: 'info', 5: 'danger' }[s] || 'info'
}

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : ''
}

async function loadAvailableOrders() {
  try {
    const res = await listAvailableOrdersAPI()
    availableOrders.value = res.data || []
  } catch { /* */ }
}

async function loadMyOrders() {
  try {
    const res = await listCourierOrdersAPI()
    myOrders.value = res.data || []
  } catch { /* */ }
}

async function handlePickup(id) {
  try {
    await ElMessageBox.confirm('确定抢这个订单？抢单后请及时取餐配送。', '确认抢单', {
      confirmButtonText: '确认抢单',
      type: 'warning',
    })
    await pickupOrderAPI(id)
    ElMessage.success('抢单成功！请及时取餐派送')
    await loadAvailableOrders()
    await loadMyOrders()
    activeTab.value = 'mine'
  } catch { /* */ }
}

async function handleDeliver(id) {
  try {
    await ElMessageBox.confirm('确认已送达？', '确认送达', {
      confirmButtonText: '确认送达',
      type: 'success',
    })
    await deliverOrderAPI(id)
    ElMessage.success('已确认送达！')
    await loadMyOrders()
    await loadAvailableOrders()
  } catch { /* */ }
}

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = location.host
  ws = new WebSocket(`${protocol}//${host}/api/merchant/ws/courier/${auth.userId}?token=${auth.token}`)

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'order_assigned' || msg.type === 'new_available') {
        ElNotification({
          title: '📋 有新订单可抢',
          message: '商家已接单，快去抢单吧！',
          type: 'warning',
          duration: 6000,
        })
        loadAvailableOrders()
      }
    } catch { /* */ }
  }

  ws.onclose = () => setTimeout(connectWebSocket, 5000)
}

function handleLogout() {
  if (ws) ws.close()
  auth.logout()
  router.push('/')
}

onMounted(() => {
  loadAvailableOrders()
  loadMyOrders()
  connectWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
})
</script>

<style scoped>
.courier-app {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f4ff 0%, #f5f7fa 100%);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 14px 24px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-brand { display: flex; align-items: center; gap: 10px; }
.header-brand h2 { font-size: 18px; color: #1a1a2e; }
.brand-icon { font-size: 24px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.user-name { color: #666; font-size: 14px; }

.main-container {
  max-width: 600px;
  margin: 16px auto;
  padding: 0 12px;
}
.main-tabs {
  background: #fff;
  border-radius: 16px;
  padding: 4px 16px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.hint { color: #999; font-size: 13px; }

.empty-state {
  text-align: center;
  padding: 48px 0;
  color: #999;
}
.empty-icon { font-size: 48px; display: block; margin-bottom: 12px; }

/* ── 订单卡片 ── */
.order-card {
  background: #fff;
  border-radius: 14px;
  padding: 18px 20px;
  margin-bottom: 12px;
  border: 1px solid #f0f0f0;
  transition: all 0.2s;
  position: relative;
}
.order-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.pickup-card { border-color: #e6a23c30; background: #fefaf3; }
.status-2 { border-left: 4px solid #409eff; }
.status-3 { border-left: 4px solid #67c23a; }

.card-badge {
  position: absolute;
  top: -8px;
  right: 16px;
  background: linear-gradient(135deg, #f5a623, #f76b1c);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 14px;
  border-radius: 20px;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.order-id { font-weight: 700; font-size: 15px; color: #1a1a2e; }
.order-time { font-size: 12px; color: #999; }

.order-dishes {
  color: #555;
  font-size: 14px;
  margin-bottom: 10px;
  line-height: 1.5;
}
.order-info-row {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
}
.order-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f5f5f5;
}
.order-total { font-size: 20px; font-weight: 700; color: #f56c6c; }
</style>
