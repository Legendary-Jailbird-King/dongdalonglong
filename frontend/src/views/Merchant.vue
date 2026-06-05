<template>
  <div class="merchant-app">
    <header class="app-header">
      <div class="header-brand">
        <span class="brand-icon">🏪</span>
        <h2>商家工作台</h2>
      </div>
      <div class="header-right">
        <el-badge :value="newOrderCount" :hidden="newOrderCount === 0" class="bell-badge">
          <span class="bell">🔔</span>
        </el-badge>
        <span class="user-name">{{ auth.userName }}</span>
        <el-button size="small" round @click="handleLogout">退出</el-button>
      </div>
    </header>

    <div class="main-container">
      <el-tabs v-model="activeTab" class="main-tabs">
        <!-- ── 订单管理 ── -->
        <el-tab-pane label="📋 订单管理" name="orders">
          <div class="toolbar">
            <el-select v-model="orderFilter" placeholder="状态筛选" clearable size="small" style="width:130px">
              <el-option :value="-1" label="全部" />
              <el-option :value="0" label="待处理" />
              <el-option :value="1" label="已接单" />
              <el-option :value="2" label="派送中" />
              <el-option :value="3" label="已完成" />
              <el-option :value="4" label="已取消" />
              <el-option :value="5" label="已拒单" />
            </el-select>
            <el-button size="small" @click="loadOrders">刷新</el-button>
          </div>

          <el-table :data="filteredOrders" stripe size="small" class="order-table"
            max-height="calc(100vh - 230px)">
            <el-table-column prop="id" label="#" width="60" />
            <el-table-column prop="dish_summary" label="餐品详情" min-width="180" show-overflow-tooltip />
            <el-table-column label="金额" width="90">
              <template #default="{ row }"><b class="price">¥{{ Number(row.total).toFixed(2) }}</b></template>
            </el-table-column>
            <el-table-column prop="shipping_address" label="地址" width="140" show-overflow-tooltip />
            <el-table-column prop="shipping_phone" label="电话" width="100" />
            <el-table-column label="状态" width="95">
              <template #default="{ row }">
                <el-tag :type="statusTag(row.status)" size="small" effect="dark">{{ row.status_text }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="order_time" label="时间" width="145">
              <template #default="{ row }">{{ formatTime(row.order_time) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="130" fixed="right">
              <template #default="{ row }">
                <template v-if="row.status === 0">
                  <el-button size="small" type="success" @click="handleAccept(row.id)">接单</el-button>
                  <el-button size="small" type="danger" @click="handleReject(row.id)">拒单</el-button>
                </template>
                <span v-else style="color:#bbb;font-size:12px">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- ── 菜品管理 ── -->
        <el-tab-pane label="🍽️ 菜品管理" name="dishes">
          <div class="toolbar">
            <el-button type="primary" size="small" @click="openDishDialog(null)">+ 添加菜品</el-button>
          </div>

          <div class="dish-grid">
            <div v-for="d in dishes" :key="d.id" class="dish-card" :class="{ deleted: d.is_deleted }">
              <div class="dish-body">
                <h4>{{ d.name }}</h4>
                <p class="dish-price">¥{{ Number(d.price).toFixed(2) }}</p>
                <div class="dish-tags">
                  <el-tag :type="d.is_active ? 'success' : 'info'" size="small">
                    {{ d.is_active ? '上架' : '下架' }}
                  </el-tag>
                  <el-tag v-if="d.is_deleted" type="danger" size="small">已删除</el-tag>
                </div>
              </div>
              <div v-if="!d.is_deleted" class="dish-actions">
                <el-button size="small" circle @click="openDishDialog(d)">✎</el-button>
                <el-button size="small" circle @click="toggleActive(d)">
                  {{ d.is_active ? '↓' : '↑' }}
                </el-button>
                <el-button size="small" circle type="danger" @click="handleDeleteDish(d.id)">✕</el-button>
              </div>
            </div>
            <el-empty v-if="dishes.length === 0" description="暂无菜品" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- ── 菜品编辑弹窗 ── -->
    <el-dialog v-model="showDishDialog" :title="editingDish ? '编辑菜品' : '添加菜品'" width="380px" class="dish-dialog">
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="dishForm.name" placeholder="菜品名称" />
        </el-form-item>
        <el-form-item label="价格 (元)">
          <el-input-number v-model="dishForm.price" :min="0" :precision="2" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDishDialog = false" round>取消</el-button>
        <el-button type="primary" @click="handleSaveDish" round>保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import {
  listMerchantDishesAPI, addDishAPI, updateDishAPI, deleteDishAPI,
  listMerchantOrdersAPI, acceptOrderAPI, rejectOrderAPI,
} from '../api/services'

const router = useRouter()
const auth = useAuthStore()

const activeTab = ref('orders')
const orderFilter = ref(-1)
const dishes = ref([])
const orders = ref([])
const newOrderCount = ref(0)

const showDishDialog = ref(false)
const editingDish = ref(null)
const dishForm = reactive({ name: '', price: 0 })

let ws = null

const filteredOrders = computed(() =>
  orderFilter.value === -1 ? orders.value : orders.value.filter(o => o.status === orderFilter.value)
)

function statusTag(s) {
  return { 0: 'warning', 1: '', 2: '', 3: 'success', 4: 'info', 5: 'danger' }[s] || 'info'
}

function formatTime(t) {
  return t ? new Date(t).toLocaleString('zh-CN') : ''
}

async function loadDishes() {
  try { const r = await listMerchantDishesAPI(); dishes.value = r.data || [] } catch { /* */ }
}

async function loadOrders() {
  try { const r = await listMerchantOrdersAPI(); orders.value = r.data || [] } catch { /* */ }
}

async function handleAccept(id) {
  try { await acceptOrderAPI(id); ElMessage.success('已接单，等待骑手抢单'); await loadOrders() } catch { /* */ }
}

async function handleReject(id) {
  try {
    await ElMessageBox.confirm('确定拒单？', '确认', { type: 'warning' })
    await rejectOrderAPI(id); ElMessage.success('已拒单'); await loadOrders()
  } catch { /* */ }
}

function openDishDialog(row) {
  editingDish.value = row
  dishForm.name = row ? row.name : ''
  dishForm.price = row ? Number(row.price) : 0
  showDishDialog.value = true
}

async function handleSaveDish() {
  if (!dishForm.name) { ElMessage.warning('请输入名称'); return }
  try {
    if (editingDish.value) {
      await updateDishAPI(editingDish.value.id, { name: dishForm.name, price: dishForm.price })
      ElMessage.success('已更新')
    } else {
      await addDishAPI({ name: dishForm.name, price: dishForm.price })
      ElMessage.success('已添加')
    }
    showDishDialog.value = false; await loadDishes()
  } catch { /* */ }
}

async function toggleActive(row) {
  try {
    await updateDishAPI(row.id, { is_active: row.is_active ? 0 : 1 })
    ElMessage.success(row.is_active ? '已下架' : '已上架'); await loadDishes()
  } catch { /* */ }
}

async function handleDeleteDish(id) {
  try {
    await ElMessageBox.confirm('确定删除？（仅软删除）', '确认', { type: 'warning' })
    await deleteDishAPI(id); ElMessage.success('已删除'); await loadDishes()
  } catch { /* */ }
}

function connectWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = location.host
  ws = new WebSocket(`${protocol}//${host}/api/merchant/ws/merchant/${auth.userId}?token=${auth.token}`)

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'new_order') {
        newOrderCount.value++
        ElNotification({
          title: '🔔 新订单提醒',
          message: msg.body || '您有新的外卖订单！',
          type: 'warning',
          duration: 6000,
        })
        loadOrders()
      }
    } catch { /* */ }
  }
  ws.onclose = () => setTimeout(connectWebSocket, 5000)
}

function handleLogout() {
  if (ws) ws.close(); auth.logout(); router.push('/')
}

onMounted(() => { loadOrders(); loadDishes(); connectWebSocket() })
onUnmounted(() => { if (ws) ws.close() })
</script>

<style scoped>
.merchant-app {
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f4ff 0%, #f5f7fa 100%);
}

.app-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  padding: 14px 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-brand { display: flex; align-items: center; gap: 10px; }
.header-brand h2 { font-size: 18px; color: #1a1a2e; }
.brand-icon { font-size: 24px; }
.header-right { display: flex; align-items: center; gap: 16px; }
.bell { font-size: 20px; cursor: pointer; }
.bell-badge :deep(.el-badge__content) { background: #f56c6c; }
.user-name { color: #666; font-size: 14px; }

.main-container {
  max-width: 1100px;
  margin: 16px auto;
  padding: 0 16px;
}
.main-tabs {
  background: #fff;
  border-radius: 16px;
  padding: 4px 20px 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}

.toolbar {
  display: flex;
  gap: 10px;
  margin: 8px 0 14px;
}

.price { color: #f56c6c; }

/* ── 菜品网格 ── */
.dish-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.dish-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fafbfc;
  border: 1px solid #f0f0f0;
  border-radius: 14px;
  padding: 16px 18px;
  transition: all 0.2s;
}
.dish-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); border-color: #d0d0f0; }
.dish-card.deleted { opacity: 0.4; pointer-events: none; }
.dish-body h4 { font-size: 15px; margin-bottom: 4px; color: #1a1a2e; }
.dish-price { color: #f56c6c; font-weight: 600; margin-bottom: 6px; }
.dish-tags { display: flex; gap: 6px; }
.dish-actions { display: flex; gap: 6px; flex-shrink: 0; }

.order-table :deep(.el-table__body tr) { cursor: default; }

.dish-dialog :deep(.el-dialog) { border-radius: 16px; }
</style>
