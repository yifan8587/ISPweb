<template>
  <el-drawer v-model="visible" :size="drawerSize" destroy-on-close @closed="handleDrawerClosed">
    <template #header>
      <div class="dh" v-if="service">
        <div class="dh-left">
          <el-tag :type="service.service_type === 'vps' ? 'primary' : 'success'">{{ service.service_type_label }}</el-tag>
          <span class="dh-no">{{ service.instance_no }}</span>
          <span class="dh-name">{{ resourceDetail?.name || service.product_name }}</span>
          <el-tag
            size="small"
            :type="service.needs_protocol_config ? 'warning' : (instanceStatusTag[service.status]?.type || 'info')"
          >
            {{ service.needs_protocol_config ? '待配置' : (instanceStatusTag[service.status]?.label || service.status) }}
          </el-tag>
        </div>
        <el-button size="small" :loading="loading" @click="reload">刷新</el-button>
      </div>
    </template>

    <div v-loading="loading">
      <el-tabs v-if="resourceDetail" v-model="tab">
        <!-- 概览 -->
        <el-tab-pane label="概览" name="overview">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="实例编号">{{ service.instance_no }}</el-descriptions-item>
            <el-descriptions-item label="产品">{{ service.product_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="节点">
              {{ service.pop_name || '—' }}
              <el-tag
                v-if="isNatDelivery"
                size="small"
                type="warning"
                style="margin-left:6px"
              >NAT 交付</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="带宽">{{ bandwidthText }}</el-descriptions-item>
            <el-descriptions-item v-if="isEdge" label="协议">{{ resourceDetail.protocol_label || '—' }}</el-descriptions-item>
            <el-descriptions-item v-if="isEdge" label="节点接口">{{ resourceDetail.node_ifname || '未下发' }}</el-descriptions-item>
            <el-descriptions-item v-if="isEdge" label="配置状态">
              <el-tag size="small" :type="resourceDetail.config_ready ? 'success' : 'warning'">
                {{ resourceDetail.config_ready ? '可下发' : '待补全' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="isEdge" label="我司对接 IP">
              <span class="mono">{{ resourceDetail.pop_mgmt_ip || '—' }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="月费">{{ money(service.monthly_fee_effective, service.fee_currency) }}</el-descriptions-item>
            <el-descriptions-item label="到期">{{ formatDate(service.expire_time) }}</el-descriptions-item>
            <el-descriptions-item label="开通">{{ formatDate(service.activated_at, true) }}</el-descriptions-item>
          </el-descriptions>

          <!-- 分配的 IP 地址（VPS / 边缘加速通用） -->
          <div style="margin-top:14px">
            <div class="sub-title">分配的 IP 地址</div>
            <el-alert
              v-if="isNatDelivery"
              type="warning"
              :closable="false"
              show-icon
              style="margin-bottom:10px"
              title="该节点为 NAT 交付"
              description="下列业务 IP 不能公网直连，请按网关与掩码在本机配置，访问需经节点 NAT。"
            />
            <div v-if="allocatedIps.length" class="table-scroll" tabindex="0" aria-label="已分配 IP 地址，可横向滚动查看全部列">
              <el-table class="ip-table" :data="allocatedIps" size="small" border>
                <el-table-column label="IP 地址">
                  <template #default="{ row }">
                    <span class="mono">{{ row.address }}<span v-if="row.prefix_len != null">/{{ row.prefix_len }}</span></span>
                  </template>
                </el-table-column>
                <el-table-column label="网关" min-width="130">
                  <template #default="{ row }">
                    <span class="mono">{{ row.gateway || '—' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="掩码" min-width="130">
                  <template #default="{ row }">
                    <span class="mono">{{ row.netmask || '—' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="主 IP" width="90">
                  <template #default="{ row }">{{ row.is_primary ? '是' : '—' }}</template>
                </el-table-column>
                <el-table-column label="状态" width="100">
                  <template #default="{ row }">
                    <el-tag size="small" :type="ipStatusTag[row.status]?.type || 'info'">
                      {{ ipStatusTag[row.status]?.label || row.status || '—' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="下发路由" min-width="140">
                  <template #default="{ row }">
                    <span class="mono">{{ row.route_cidr || `${row.address}/32` }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="路由状态" width="110">
                  <template #default="{ row }">
                    <el-tag size="small" :type="row.route_status === 'pushed' ? 'success' : 'warning'">
                      {{ row.route_status_label || (row.route_status === 'pushed' ? '已下发' : '待下发') }}
                    </el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <el-empty v-else description="暂无分配的 IP" :image-size="60" />
          </div>
        </el-tab-pane>

        <!-- VPS 配置 -->
        <el-tab-pane v-if="isVps" label="配置信息" name="config">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom:16px"
            title="调整 CPU / 内存 / 硬盘、带宽和增减公网 IP 请到「我的服务」提交变更。确认后由 ISPmanager 下发到对应 POP 的 PVE。"
          />
          <el-button type="primary" style="margin-bottom:16px" @click="goChangeService">去变更带宽 / IP</el-button>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="VPS ID">{{ resourceDetail.vps_no }}</el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag size="small" :type="vpsStatusTag[resourceDetail.status]?.type">{{ resourceDetail.status_label }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="vCPU">{{ resourceDetail.vcpu }} 核</el-descriptions-item>
            <el-descriptions-item label="内存">{{ ramText(resourceDetail.ram_mb) }}</el-descriptions-item>
            <el-descriptions-item label="硬盘">{{ resourceDetail.disk_gb }} GB</el-descriptions-item>
            <el-descriptions-item label="带宽">{{ resourceDetail.bandwidth_mbps }} Mbps</el-descriptions-item>
            <el-descriptions-item label="系统">{{ resourceDetail.os_label }} {{ resourceDetail.os_version || '' }}</el-descriptions-item>
            <el-descriptions-item label="内核">{{ resourceDetail.kernel_version || '—' }}</el-descriptions-item>
            <el-descriptions-item label="管理 IP">
              <span class="mono">{{ resourceDetail.mgmt_ip || '—' }}</span>
              <span v-if="resourceDetail.mgmt_ip">:{{ resourceDetail.mgmt_port }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="SSH 用户">{{ resourceDetail.mgmt_username || 'root' }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="resourceDetail.ip_list?.length" style="margin-top:14px">
            <div class="sub-title">公网 IP</div>
            <el-tag v-for="ip in resourceDetail.ip_list" :key="ip.id" style="margin:4px" :type="ip.is_primary ? 'success' : 'info'">
              {{ ip.address }}/{{ ip.prefix_len }}
              <span v-if="ip.gateway" style="margin-left:6px;font-weight:400">gw {{ ip.gateway }}</span>
              <span v-if="ip.netmask" style="margin-left:6px;font-weight:400">{{ ip.netmask }}</span>
            </el-tag>
          </div>
          <div v-if="resourceDetail.interfaces?.length" style="margin-top:14px">
            <div class="sub-title">网络接口</div>
            <div class="table-scroll" tabindex="0" aria-label="网络接口列表，可横向滚动查看全部列">
              <el-table class="interfaces-table" :data="resourceDetail.interfaces" size="small" border>
                <el-table-column prop="ifname" label="接口" />
                <el-table-column prop="mac_address" label="MAC" />
                <el-table-column prop="bandwidth_mbps" label="带宽(Mbps)" width="110" />
                <el-table-column label="主接口" width="80">
                  <template #default="{ row }">{{ row.is_primary ? '是' : '—' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- VPS 运维 -->
        <el-tab-pane v-if="isVps" label="运维操作" name="ops">
          <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px"
                    title="电源与密码操作将提交到节点执行；控制台通过 noVNC 连接。" />
          <div v-if="caps.vps_manage" class="ops-grid">
            <el-button type="warning" :loading="acting === 'restart'" @click="doPower('restart')">重启</el-button>
            <el-button :loading="acting === 'start'" @click="doPower('start')">启动</el-button>
            <el-button :loading="acting === 'shutdown'" @click="doPower('shutdown')">关机</el-button>
            <el-button type="primary" :disabled="!resourceDetail.has_console" @click="openConsole">noVNC 控制台</el-button>
            <el-button :loading="acting === 'sync'" @click="doSync">同步状态</el-button>
          </div>
          <template v-if="caps.vps_manage">
          <el-divider content-position="left">修改登录密码</el-divider>
          <el-form label-position="top" style="max-width:420px" @submit.prevent="doSetPassword">
            <el-form-item label="用户名">
              <el-input v-model="newUsername" placeholder="默认使用当前 SSH 用户" />
            </el-form-item>
            <el-form-item label="新密码">
              <div class="pwd-row">
                <el-input v-model="newPassword" type="password" show-password placeholder="至少 8 位，将下发到虚机" />
                <el-button @click="generateOpsPassword">生成</el-button>
              </div>
            </el-form-item>
            <el-button type="primary" :loading="acting === 'pwd'" @click="doSetPassword">保存并下发</el-button>
          </el-form>
          </template>
        </el-tab-pane>

        <!-- VPS 流量 -->
        <el-tab-pane v-if="isVps" label="流量监控" name="traffic">
          <div class="monitor-toolbar">
            <div class="monitor-toolbar-left">
              <span class="monitor-range-label">时间范围</span>
              <el-radio-group v-model="trafficRangeMode" size="small" aria-label="流量时间范围模式">
                <el-radio-button value="preset">快捷</el-radio-button>
                <el-radio-button value="custom">自定义</el-radio-button>
              </el-radio-group>
              <el-select
                v-if="trafficRangeMode === 'preset'"
                id="traffic-hours"
                v-model="monitorHours"
                size="small"
                class="monitor-range"
                aria-label="流量监控快捷时间范围"
              >
                <el-option v-for="option in monitorRangeOptions" :key="option.hours" :label="option.label" :value="option.hours" />
              </el-select>
              <el-date-picker
                v-else
                v-model="trafficCustomRange"
                type="datetimerange"
                size="small"
                class="monitor-datetime"
                unlink-panels
                range-separator="至"
                start-placeholder="起始时间"
                end-placeholder="终止时间"
                value-format="YYYY-MM-DDTHH:mm:ss"
                :disabled-date="disabledTrafficDate"
                aria-label="流量监控自定义时间范围"
              />
              <el-button
                v-if="trafficRangeMode === 'custom'"
                size="small"
                type="primary"
                :loading="loadingTraffic"
                @click="applyTrafficCustomRange"
              >
                查询
              </el-button>
              <span class="monitor-updated">最后更新：{{ trafficUpdatedAt ? formatDate(trafficUpdatedAt, true) : '—' }}</span>
            </div>
            <el-button size="small" :loading="loadingTraffic" title="刷新流量监控数据" @click="loadTraffic">刷新</el-button>
          </div>
          <el-alert v-if="trafficError" type="error" :closable="false" show-icon :title="trafficError" class="monitor-error" />
          <MonitorTraffic :data="trafficData" :loading="loadingTraffic" />
        </el-tab-pane>

        <el-tab-pane v-if="isVps" label="重装系统" name="reinstall">
          <el-form v-if="caps.vps_manage" label-position="top" style="max-width:420px">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              style="margin-bottom:16px"
              title="运行中的虚机会先关机，确认停机后再开始重装。"
            />
            <el-form-item label="系统镜像">
              <el-select v-model="reinstallForm.os_image" placeholder="选择镜像" style="width:100%">
                <el-option v-for="img in osImages" :key="img.id" :label="`${img.name} ${img.version || ''}`.trim()" :value="img.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="登录用户名（可选）">
              <el-input v-model="reinstallForm.username" placeholder="默认随所选系统，如 ubuntu / debian" />
            </el-form-item>
            <el-form-item label="新登录密码（可选）">
              <div class="pwd-row">
                <el-input v-model="reinstallForm.password" type="password" show-password placeholder="至少 8 位，可留空" />
                <el-button @click="generateReinstallPassword">生成</el-button>
              </div>
            </el-form-item>
            <el-button type="danger" :loading="acting === 'reinstall'" @click="doReinstall">
              {{ reinstallActionLabel }}
            </el-button>
          </el-form>
          <el-divider content-position="left">最近任务</el-divider>
          <el-table :data="selfJobs.filter((j) => j.job_type === 'reinstall')" size="small" border>
            <el-table-column prop="job_no" label="编号" width="160" />
            <el-table-column prop="status_label" label="状态" width="100" />
            <el-table-column prop="result_message" label="摘要" min-width="180" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane v-if="isVps" label="快照" name="snapshots">
          <el-alert type="info" :closable="false" show-icon style="margin-bottom:16px"
                    title="快照只记档案与任务进度。节点 PVE snapshot 接口预留，达到保留份数时会过期最早的可用快照。" />
          <div v-if="caps.vps_manage" class="ops-grid" style="margin-bottom:16px">
            <el-input v-model="snapshotName" placeholder="快照名称（可空）" style="max-width:240px" />
            <el-button type="primary" :loading="acting === 'snapshot'" @click="doCreateSnapshot">创建快照</el-button>
          </div>
          <el-table :data="snapshots" v-loading="snapLoading" size="small" border>
            <el-table-column prop="snapshot_no" label="编号" width="160" />
            <el-table-column prop="name" label="名称" min-width="140" />
            <el-table-column prop="status_label" label="状态" width="90" />
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button v-if="caps.vps_manage && row.status === 'ready'" link type="primary" @click="doRestoreSnapshot(row)">恢复</el-button>
                <el-button v-if="caps.vps_manage && row.status !== 'restoring' && row.status !== 'deleted'" link type="danger" @click="doDeleteSnapshot(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Edge 协议配置 -->
        <el-tab-pane v-if="isEdge" label="协议配置" name="edge-config">
          <el-steps :active="wizardStep" finish-status="success" align-center class="config-steps">
            <el-step title="选择协议" />
            <el-step title="补全配置" />
            <el-step title="保存配置" />
            <el-step :title="resourceDetail.protocol === 'socks5' ? '完成' : '写入后台'" />
          </el-steps>

          <el-alert
            v-if="resourceDetail.needs_protocol_config || !resourceDetail.config_ready"
            type="warning"
            :closable="false"
            show-icon
            class="wizard-alert"
            title="购买后仅预分配了带宽与业务 IP。请按步骤选择 GRE 或 WireGuard，补全对端参数后再保存并写入节点。"
          />

          <!-- 步骤 1：选择协议 -->
          <div v-show="wizardStep === 0" class="wizard-pane">
            <div class="proto-picker">
              <div class="proto-label">第一步：选择对接协议</div>
              <el-radio-group
                v-model="selectedProtocol"
                :disabled="!caps.edge_manage || !switchableProtocols.length"
              >
                <el-radio-button v-for="p in switchableProtocols" :key="p" :value="p">
                  {{ p === 'wireguard' ? 'WireGuard' : 'GRE' }}
                </el-radio-button>
              </el-radio-group>
              <p class="field-tip">同一条公网对接只能选择 GRE 或 WireGuard。改成另一种协议时，会先删除当前协议配置，再使用已分配的隧道地址重新配置。</p>
            </div>
            <div v-if="configChecklist.length" class="checklist">
              <div class="sub-title">系统已预分配</div>
              <el-table :data="configChecklist" size="small" border>
                <el-table-column prop="label" label="项目" min-width="180" />
                <el-table-column label="取值" min-width="200">
                  <template #default="{ row }">
                    <span class="mono">{{ row.value || '—' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="来源" width="90">
                  <template #default="{ row }">{{ row.source === 'system' ? '系统' : '待您填写' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </div>

          <!-- 步骤 2：补全数据 -->
          <div v-show="wizardStep === 1" class="wizard-pane">
            <div v-if="clientGuide?.notes?.length" class="client-guide">
              <div class="sub-title">您侧隧道需要配置</div>
              <ul>
                <li v-for="(line, idx) in clientGuide.notes" :key="idx">{{ line }}</li>
              </ul>
            </div>
            <template v-if="resourceDetail.protocol === 'gre'">
              <el-alert type="info" :closable="false" show-icon style="margin-bottom:14px"
                        title="GRE 隧道配置说明">
                <div class="cfg-note">
                  <p>· <b>本端 IP</b>：我司机房端固定地址，系统自动分配，<b>不可修改</b>。</p>
                  <p>· <b>远端 IP</b>：您的<b>客户端公网 IP</b>，用于建立 GRE 隧道对端。</p>
                  <p>· <b>隧道 IP/CIDR</b>：两端互通的内网地址，<b>建议使用 /30 网段</b>（如 10.21.0.1/30）。</p>
                </div>
              </el-alert>
              <el-form ref="greFormRef" :model="edgeForm" :rules="greRules" label-width="120px" style="max-width:600px">
                <el-form-item label="本端 IP" prop="local_ip">
                  <el-input v-model="edgeForm.local_ip" disabled />
                  <div class="field-tip">我司对接地址（POP 管理 IP），不可修改</div>
                </el-form-item>
                <el-form-item label="远端 IP" prop="remote_ip">
                  <el-input v-model="edgeForm.remote_ip" placeholder="客户端公网 IP" />
                  <div class="field-tip">* 您的公网 IP，建立 GRE 对端</div>
                </el-form-item>
                <el-form-item label="隧道 IP/CIDR" prop="tunnel_ip">
                  <el-input v-model="edgeForm.tunnel_ip" :disabled="fieldLocked('tunnel_ip')" placeholder="由系统分配，如 10.21.0.1/30" />
                  <div class="field-tip">{{ fieldLocked('tunnel_ip') ? '系统已从隧道地址段分配，不可修改' : '两端互通内网地址，建议 /30' }}</div>
                </el-form-item>
                <el-form-item label="PMTUD">
                  <el-switch v-model="edgeForm.pmtud" />
                </el-form-item>
                <el-form-item label="Checksum">
                  <el-switch v-model="edgeForm.checksum" />
                </el-form-item>
              </el-form>
            </template>
            <template v-else-if="resourceDetail.protocol === 'wireguard'">
              <el-form label-width="140px" style="max-width:620px">
                <el-form-item label="监听端口">
                  <el-input-number v-model="edgeForm.listen_port" :min="51820" :max="65535" disabled />
                  <div class="field-tip">从 51820 起按客户依次分配，每个客户端口不同，不可修改</div>
                </el-form-item>
                <el-form-item label="接口 IP/CIDR">
                  <el-input v-model="edgeForm.interface_ip" disabled />
                  <div class="field-tip">已读取分配的隧道 IP，不可修改</div>
                </el-form-item>
                <el-form-item label="本端私钥">
                  <el-input v-model="edgeForm.private_key" type="password" show-password :disabled="Boolean(resourceDetail.has_private_key || resourceDetail.wg_config?.has_private_key)" />
                  <el-button
                    v-if="caps.edge_manage && !resourceDetail.wg_config?.has_private_key"
                    link
                    type="primary"
                    style="margin-left:8px"
                    :loading="acting === 'wgkey'"
                    @click="genWgKey"
                  >生成密钥</el-button>
                </el-form-item>
                <el-form-item label="本端公钥"><el-input v-model="edgeForm.public_key" disabled /></el-form-item>
                <el-form-item label="对端公钥">
                  <el-input v-model="edgeForm.peer_public_key" placeholder="填写您侧 WireGuard 的公钥" />
                  <div class="field-tip">这是您自己的公钥。不能填写上方的本端公钥，否则节点无法建立隧道。</div>
                </el-form-item>
                <el-form-item label="对端 Endpoint"><el-input v-model="edgeForm.peer_endpoint" placeholder="1.2.3.4:51820" /></el-form-item>
                <el-form-item label="Allowed IPs">
                  <el-input v-model="edgeForm.peer_allowed_ips" placeholder="留空则使用已分配业务 IP/32，例如 192.168.10.1/32" />
                  <div class="field-tip">WireGuard 用这里的 AllowedIPs 下发业务路由，不会再单独配置静态路由。</div>
                </el-form-item>
                <el-form-item label="Keepalive"><el-input-number v-model="edgeForm.persistent_keepalive" :min="0" :max="300" /></el-form-item>
                <el-form-item label="MTU"><el-input-number v-model="edgeForm.mtu" :min="1280" :max="9000" /></el-form-item>
              </el-form>
            </template>
            <template v-else-if="resourceDetail.protocol === 'socks5'">
              <el-form label-width="120px" style="max-width:520px">
                <el-form-item label="监听 IP"><el-input v-model="edgeForm.listen_ip" /></el-form-item>
                <el-form-item label="监听端口"><el-input-number v-model="edgeForm.listen_port" :min="1" :max="65535" /></el-form-item>
                <el-form-item label="需要认证"><el-switch v-model="edgeForm.auth_required" /></el-form-item>
                <el-form-item v-if="edgeForm.auth_required" label="用户名"><el-input v-model="edgeForm.username" /></el-form-item>
                <el-form-item v-if="edgeForm.auth_required" label="密码"><el-input v-model="edgeForm.password" type="password" show-password /></el-form-item>
                <el-form-item label="UDP 转发"><el-switch v-model="edgeForm.udp_enabled" /></el-form-item>
              </el-form>
            </template>
          </div>

          <!-- 步骤 3：核对并保存 -->
          <div v-show="wizardStep === 2" class="wizard-pane">
            <div class="sub-title">请核对将保存的配置</div>
            <el-descriptions :column="1" border size="small" class="review-desc">
              <el-descriptions-item v-for="row in wizardReviewRows" :key="row.label" :label="row.label">
                <span class="mono">{{ row.value || '—' }}</span>
              </el-descriptions-item>
            </el-descriptions>
            <el-alert
              v-if="configSaved"
              type="success"
              :closable="false"
              show-icon
              class="wizard-alert"
              title="配置已保存到档案，可以进行下一步写入后台。"
            />
          </div>

          <!-- 步骤 4：写入后台 -->
          <div v-show="wizardStep === 3" class="wizard-pane">
            <template v-if="resourceDetail.protocol === 'socks5'">
              <el-alert type="success" :closable="false" show-icon title="Socks5 配置已保存。该协议暂不支持自动写入节点。" />
            </template>
            <template v-else>
              <p class="field-tip" style="margin-bottom:12px">将把已保存的隧道配置写入节点并即时生效。过程中会反馈各步骤状态。</p>
              <div class="push-steps">
                <div v-for="step in pushProgress" :key="step.key" class="push-step" :class="step.status">
                  <el-icon v-if="step.status === 'done'"><CircleCheckFilled /></el-icon>
                  <el-icon v-else-if="step.status === 'error'"><CircleCloseFilled /></el-icon>
                  <el-icon v-else-if="step.status === 'warn'"><WarnTriangleFilled /></el-icon>
                  <el-icon v-else-if="step.status === 'running'" class="is-loading"><Loading /></el-icon>
                  <el-icon v-else><Clock /></el-icon>
                  <div>
                    <div class="push-label">{{ step.label }}</div>
                    <div v-if="step.detail" class="push-detail">{{ step.detail }}</div>
                  </div>
                </div>
              </div>
              <el-alert
                v-if="pushSucceeded"
                type="success"
                :closable="false"
                show-icon
                class="wizard-alert"
                :title="pushResultText || '已写入节点并生效，服务状态已更新。'"
              />
            </template>
          </div>

          <div class="edge-actions">
            <el-button v-if="wizardStep > 0 && !pushSucceeded" @click="wizardBack">上一步</el-button>
            <el-button v-if="wizardStep === 0 && caps.edge_manage" type="primary" @click="wizardNext">下一步</el-button>
            <el-button v-if="wizardStep === 1 && caps.edge_manage" type="primary" @click="wizardNext">下一步</el-button>
            <el-button
              v-if="wizardStep === 2 && caps.edge_manage"
              type="primary"
              :loading="acting === 'save'"
              @click="wizardSave"
            >保存配置</el-button>
            <el-button
              v-if="wizardStep === 3 && caps.edge_manage && resourceDetail.protocol !== 'socks5' && !pushSucceeded"
              type="success"
              :loading="acting === 'push'"
              @click="wizardPush"
            >写入后台并生效</el-button>
            <el-button v-if="pushSucceeded" type="primary" @click="finishWizard">查看服务概览</el-button>
          </div>
        </el-tab-pane>

        <!-- Edge 流量 / 品质 -->
        <el-tab-pane v-if="isEdge" label="流量监控" name="traffic">
          <div class="monitor-toolbar">
            <div class="monitor-toolbar-left">
              <span class="monitor-range-label">时间范围</span>
              <el-radio-group v-model="trafficRangeMode" size="small" aria-label="流量时间范围模式">
                <el-radio-button value="preset">快捷</el-radio-button>
                <el-radio-button value="custom">自定义</el-radio-button>
              </el-radio-group>
              <el-select
                v-if="trafficRangeMode === 'preset'"
                id="edge-traffic-hours"
                v-model="monitorHours"
                size="small"
                class="monitor-range"
                aria-label="流量监控快捷时间范围"
              >
                <el-option v-for="option in monitorRangeOptions" :key="option.hours" :label="option.label" :value="option.hours" />
              </el-select>
              <el-date-picker
                v-else
                v-model="trafficCustomRange"
                type="datetimerange"
                size="small"
                class="monitor-datetime"
                unlink-panels
                range-separator="至"
                start-placeholder="起始时间"
                end-placeholder="终止时间"
                value-format="YYYY-MM-DDTHH:mm:ss"
                :disabled-date="disabledTrafficDate"
                aria-label="流量监控自定义时间范围"
              />
              <el-button
                v-if="trafficRangeMode === 'custom'"
                size="small"
                type="primary"
                :loading="loadingTraffic"
                @click="applyTrafficCustomRange"
              >
                查询
              </el-button>
              <span class="monitor-updated">最后更新：{{ trafficUpdatedAt ? formatDate(trafficUpdatedAt, true) : '—' }}</span>
            </div>
            <el-button size="small" :loading="loadingTraffic" title="刷新流量监控数据" @click="loadTraffic">刷新</el-button>
          </div>
          <el-alert v-if="trafficError" type="error" :closable="false" show-icon :title="trafficError" class="monitor-error" />
          <MonitorTraffic :data="trafficData" :loading="loadingTraffic" />
        </el-tab-pane>
        <el-tab-pane v-if="isEdge" label="品质监控" name="quality">
          <div class="monitor-toolbar">
            <div class="monitor-toolbar-left">
              <label class="monitor-range-label" for="quality-hours">时间范围</label>
              <el-select id="quality-hours" v-model="monitorHours" size="small" class="monitor-range" aria-label="品质监控时间范围">
                <el-option v-for="option in monitorRangeOptions" :key="option.hours" :label="option.label" :value="option.hours" />
              </el-select>
              <span class="monitor-updated">最后更新：{{ qualityUpdatedAt ? formatDate(qualityUpdatedAt, true) : '—' }}</span>
            </div>
            <el-button size="small" :loading="loadingQuality" title="刷新品质监控数据" @click="loadQuality">刷新</el-button>
          </div>
          <el-alert v-if="qualityError" type="error" :closable="false" show-icon :title="qualityError" class="monitor-error" />
          <MonitorQuality :data="qualityData" :loading="loadingQuality" />
        </el-tab-pane>
      </el-tabs>
    </div>
  </el-drawer>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  edgeWgGenkey, getEdgeQuality, getEdgeTraffic, getMyEdgeDetail,
  createVPSSnapshot, deleteVPSSnapshot, getMyVPSDetail, getOsImages, getVPSSelfServiceJobs,
  getVPSSnapshots, getVPSTraffic, pushEdgeToNode, reinstallVPS, restoreVPSSnapshot,
  setVPSRootPassword, syncVPSNow, updateEdgeProtocolConfig, vpsPower,
} from '@/api'
import MonitorQuality from './components/MonitorQuality.vue'
import MonitorTraffic from './components/MonitorTraffic.vue'
import { confirmPortalEdgePush } from '@/composables/useConfirmPush'
import { useCapabilities } from '@/composables/useCapabilities'
import { formatDate, instanceStatusTag, money, ramText, vpsStatusTag } from '@/utils/format'

const props = defineProps({
  modelValue: Boolean,
  service: Object,
})
const emit = defineEmits(['update:modelValue', 'closed', 'refresh'])
const { caps } = useCapabilities()

const router = useRouter()
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const tab = ref('overview')
const loading = ref(false)
const resourceDetail = ref(null)
const trafficData = ref(null)
const qualityData = ref(null)
const loadingTraffic = ref(false)
const loadingQuality = ref(false)
const trafficError = ref('')
const qualityError = ref('')
const monitorHours = ref(24)
const trafficRangeMode = ref('preset')
const trafficCustomRange = ref(null)
const appliedTrafficRange = ref(null)
const documentIsVisible = ref(typeof document === 'undefined' || document.visibilityState !== 'hidden')
const narrowViewport = ref(false)
const acting = ref('')
const newPassword = ref('')
const newUsername = ref('')
const osImages = ref([])
const snapshots = ref([])
const selfJobs = ref([])
const snapLoading = ref(false)
const snapshotName = ref('')
const reinstallForm = reactive({ os_image: null, username: '', password: '' })
const reinstallHint = ref('')
const reinstallActionLabel = computed(() => reinstallHint.value || '提交重装')
const edgeForm = reactive({})
const selectedProtocol = ref('gre')
const greFormRef = ref(null)
const wizardStep = ref(0)
const configSaved = ref(false)
const pushSucceeded = ref(false)
const pushResultText = ref('')
const pushProgress = ref([])
const monitorRangeOptions = [
  { label: '近 1 小时', hours: 1 },
  { label: '近 6 小时', hours: 6 },
  { label: '近 24 小时', hours: 24 },
  { label: '近 7 天', hours: 168 },
]
const MAX_TRAFFIC_RANGE_MS = 168 * 3600 * 1000
const trafficRequests = new Map()
const qualityRequests = new Map()
let monitorTimer = null
let monitorPollRun = 0
let narrowViewportQuery
let lastOpenedResourceKey = null

const IP_RE = /^(\d{1,3}\.){3}\d{1,3}$/
const CIDR_RE = /^(\d{1,3}\.){3}\d{1,3}\/\d{1,2}$/
const greRules = {
  remote_ip: [
    { required: true, message: '请输入远端(客户端) IP', trigger: 'blur' },
    { pattern: IP_RE, message: 'IP 格式不正确', trigger: 'blur' },
  ],
  tunnel_ip: [
    { required: true, message: '请输入隧道 IP/CIDR', trigger: 'blur' },
    { pattern: CIDR_RE, message: '请使用 CIDR 格式，如 10.21.0.1/30', trigger: 'blur' },
  ],
}

async function validateGreForm() {
  if (resourceDetail.value?.protocol !== 'gre') return true
  if (greFormRef.value) {
    const ok = await greFormRef.value.validate().catch(() => false)
    if (!ok) return false
  }
  if (edgeForm.remote_ip && edgeForm.remote_ip === edgeForm.local_ip) {
    ElMessage.error('远端 IP 不能与本端 IP 相同')
    return false
  }
  return true
}

const isVps = computed(() => props.service?.service_type === 'vps')
const isEdge = computed(() => props.service?.service_type === 'edge')
const switchableProtocols = computed(() => {
  const raw = resourceDetail.value?.allowed_protocols
  const types = Array.isArray(raw) ? raw.filter((p) => p === 'gre' || p === 'wireguard') : []
  return types.length ? types : ['gre', 'wireguard']
})
const resourceId = computed(() => props.service?.resource?.id)
const drawerSize = computed(() => (narrowViewport.value ? '100%' : '78%'))
const activeMonitor = computed(() => (['traffic', 'quality'].includes(tab.value) ? tab.value : ''))
const shouldPollMonitor = computed(() => (
  visible.value
  && Boolean(resourceId.value)
  && Boolean(activeMonitor.value)
  && documentIsVisible.value
  && (activeMonitor.value !== 'traffic' || Boolean(getTrafficQueryParams()))
))
const trafficUpdatedAt = computed(() => trafficData.value?.updated_at || '')
const qualityUpdatedAt = computed(() => qualityData.value?.updated_at || '')

// 分配的 IP / 带宽（VPS 与边缘加速详情接口均返回 ip_list、bandwidth_mbps）
const allocatedIps = computed(() => resourceDetail.value?.ip_list || [])
const isNatDelivery = computed(() => (
  resourceDetail.value?.ip_delivery_mode === 'nat'
  || props.service?.ip_delivery_mode === 'nat'
))
const configChecklist = computed(() => resourceDetail.value?.config_checklist || [])
const clientGuide = computed(() => resourceDetail.value?.client_tunnel_guide || null)
const bandwidthText = computed(() => {
  const bw = resourceDetail.value?.bandwidth_mbps
  return bw != null && bw !== '' ? `${bw} Mbps` : '—'
})
const ipStatusTag = {
  assigned: { label: '已分配', type: 'success' },
  reserved: { label: '已保留', type: 'warning' },
  available: { label: '可用', type: 'info' },
  blocked: { label: '封禁', type: 'danger' },
  system: { label: '系统', type: 'info' },
}

function fieldLocked(key) {
  const item = configChecklist.value.find((row) => row.key === key)
  if (item) return item.editable === false && Boolean(item.value)
  if (key === 'local_ip') return Boolean(edgeForm.local_ip || resourceDetail.value?.pop_mgmt_ip)
  if (key === 'tunnel_ip') return Boolean(resourceDetail.value?.gre_config?.tunnel_ip)
  if (key === 'interface_ip') return Boolean(resourceDetail.value?.wg_config?.interface_ip)
  return false
}

function protocolLabel(proto) {
  if (proto === 'wireguard') return 'WireGuard'
  if (proto === 'gre') return 'GRE'
  return proto || '当前协议'
}

async function applyProtocolChoice() {
  const next = selectedProtocol.value
  if (!next || !resourceId.value) return false
  const saved = resourceDetail.value?.protocol
  if (saved === next) return true
  const fromLabel = protocolLabel(saved)
  const toLabel = protocolLabel(next)
  try {
    await ElMessageBox.confirm(
      `当前配置为 ${fromLabel}。切换为 ${toLabel} 会先删除 ${fromLabel} 配置，再按已分配的隧道地址配置 ${toLabel}。`,
      '切换对接协议',
      { type: 'warning', confirmButtonText: '删除并切换', cancelButtonText: '取消' },
    )
  } catch {
    selectedProtocol.value = saved || next
    return false
  }
  const res = await updateEdgeProtocolConfig(resourceId.value, { protocol: next })
  resourceDetail.value = res.data || res
  fillEdgeForm(resourceDetail.value)
  return true
}

function fillEdgeForm(detail) {
  selectedProtocol.value = detail.protocol || 'gre'
  Object.keys(edgeForm).forEach((k) => delete edgeForm[k])
  const proto = detail.protocol
  if (proto === 'gre') {
    Object.assign(edgeForm, {
      local_ip: detail.gre_config?.local_ip || detail.pop_mgmt_ip || '',
      remote_ip: detail.gre_config?.remote_ip || '',
      tunnel_ip: detail.gre_config?.tunnel_ip || '',
      pmtud: detail.gre_config?.pmtud !== false,
      checksum: !!detail.gre_config?.checksum,
      mtu: detail.gre_config?.mtu ?? 1400,
    })
  } else if (proto === 'wireguard') {
    Object.assign(edgeForm, {
      ...(detail.wg_config || {}),
      private_key: '',
      listen_port: detail.wg_config?.listen_port || 51820,
      interface_ip: detail.wg_config?.interface_ip || detail.gre_config?.tunnel_ip || '',
      public_key: detail.wg_config?.public_key || '',
    })
  } else if (proto === 'socks5' && detail.socks5_config) {
    Object.assign(edgeForm, { ...detail.socks5_config, password: '' })
  }
}

async function reload() {
  if (!resourceId.value) return
  loading.value = true
  try {
    if (isVps.value) {
      resourceDetail.value = await getMyVPSDetail(resourceId.value)
      newUsername.value = resourceDetail.value?.mgmt_username || newUsername.value
      await loadSelfService()
    } else if (isEdge.value) {
      const raw = await getMyEdgeDetail(resourceId.value)
      resourceDetail.value = raw?.data && raw.data.id ? raw.data : raw
      fillEdgeForm(resourceDetail.value)
      if (resourceDetail.value?.config_ready === false || resourceDetail.value?.needs_protocol_config) {
        tab.value = 'edge-config'
      }
    }
  } finally {
    loading.value = false
  }
}

async function loadTraffic() {
  if (!resourceId.value) return null
  const params = getTrafficQueryParams()
  if (!params) {
    ElMessage.warning('请选择起始时间与终止时间后查询')
    return null
  }
  const requestKey = getTrafficRequestKey(params)
  if (trafficRequests.has(requestKey)) return trafficRequests.get(requestKey)

  trafficError.value = ''
  loadingTraffic.value = true
  const task = (async () => {
    try {
      const res = isVps.value
        ? await getVPSTraffic(resourceId.value, params)
        : await getEdgeTraffic(resourceId.value, params)
      const data = unwrapMonitorData(res, '流量')
      if (isCurrentTrafficRequest(requestKey)) trafficData.value = data
      return data
    } catch (error) {
      if (isCurrentTrafficRequest(requestKey)) {
        trafficData.value = null
        trafficError.value = `流量监控加载失败：${monitorErrorMessage(error)}`
      }
      return null
    } finally {
      trafficRequests.delete(requestKey)
      loadingTraffic.value = trafficRequests.size > 0
    }
  })()
  trafficRequests.set(requestKey, task)
  return task
}

async function loadQuality() {
  if (!resourceId.value) return null
  const requestKey = getQualityRequestKey()
  if (qualityRequests.has(requestKey)) return qualityRequests.get(requestKey)

  qualityError.value = ''
  loadingQuality.value = true
  const task = (async () => {
    try {
      const res = await getEdgeQuality(resourceId.value, { hours: monitorHours.value })
      const data = unwrapMonitorData(res, '品质')
      if (isCurrentQualityRequest(requestKey)) qualityData.value = data
      return data
    } catch (error) {
      if (isCurrentQualityRequest(requestKey)) {
        qualityData.value = null
        qualityError.value = `品质监控加载失败：${monitorErrorMessage(error)}`
      }
      return null
    } finally {
      qualityRequests.delete(requestKey)
      loadingQuality.value = qualityRequests.size > 0
    }
  })()
  qualityRequests.set(requestKey, task)
  return task
}

function padTime(value) {
  return String(value).padStart(2, '0')
}

function toLocalDateTimeString(date) {
  return `${date.getFullYear()}-${padTime(date.getMonth() + 1)}-${padTime(date.getDate())}T${padTime(date.getHours())}:${padTime(date.getMinutes())}:${padTime(date.getSeconds())}`
}

function buildPresetTrafficRange(hours = monitorHours.value) {
  const end = new Date()
  const start = new Date(end.getTime() - hours * 3600 * 1000)
  return [toLocalDateTimeString(start), toLocalDateTimeString(end)]
}

function getTrafficQueryParams() {
  if (trafficRangeMode.value === 'custom') {
    const range = appliedTrafficRange.value
    if (!Array.isArray(range) || range.length !== 2 || !range[0] || !range[1]) return null
    return { time_from: range[0], time_till: range[1] }
  }
  return { hours: monitorHours.value }
}

function getTrafficRequestKey(params = getTrafficQueryParams()) {
  if (!params) return `${props.service?.service_type || ''}:${resourceId.value}:traffic:pending`
  if (params.time_from) {
    return `${props.service?.service_type || ''}:${resourceId.value}:traffic:custom:${params.time_from}:${params.time_till}`
  }
  return `${props.service?.service_type || ''}:${resourceId.value}:traffic:hours:${params.hours}`
}

function getQualityRequestKey() {
  return `${props.service?.service_type || ''}:${resourceId.value}:quality:${monitorHours.value}`
}

function isCurrentTrafficRequest(requestKey) {
  return visible.value && requestKey === getTrafficRequestKey()
}

function isCurrentQualityRequest(requestKey) {
  return visible.value && requestKey === getQualityRequestKey()
}

function disabledTrafficDate(date) {
  const today = new Date()
  today.setHours(23, 59, 59, 999)
  return date.getTime() > today.getTime()
}

function validateTrafficCustomRange(range) {
  if (!Array.isArray(range) || range.length !== 2 || !range[0] || !range[1]) {
    return '请选择起始时间与终止时间'
  }
  const start = new Date(range[0])
  const end = new Date(range[1])
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return '时间格式无效'
  }
  if (start >= end) {
    return '起始时间必须早于终止时间'
  }
  const span = end.getTime() - start.getTime()
  if (span < 60 * 1000) {
    return '时间范围至少 1 分钟'
  }
  if (span > MAX_TRAFFIC_RANGE_MS) {
    return '时间范围最长 7 天'
  }
  if (end.getTime() > Date.now() + 5 * 60 * 1000) {
    return '终止时间不能晚于当前时间'
  }
  return ''
}

function applyTrafficCustomRange() {
  const error = validateTrafficCustomRange(trafficCustomRange.value)
  if (error) {
    ElMessage.warning(error)
    return
  }
  appliedTrafficRange.value = [...trafficCustomRange.value]
  trafficData.value = null
  trafficError.value = ''
  syncMonitorPolling()
}

function resetTrafficRangeState() {
  trafficRangeMode.value = 'preset'
  monitorHours.value = 24
  trafficCustomRange.value = null
  appliedTrafficRange.value = null
}

function unwrapMonitorData(res, name) {
  if (res?.data && typeof res.data === 'object') return res.data
  throw new Error(res?.message || `${name}监控响应格式异常`)
}

function monitorErrorMessage(error) {
  return error?.response?.data?.message
    || error?.response?.data?.detail
    || error?.message
    || '请稍后重试'
}

function stopMonitorPolling() {
  monitorPollRun += 1
  if (monitorTimer !== null) {
    window.clearTimeout(monitorTimer)
    monitorTimer = null
  }
}

async function pollActiveMonitor(run) {
  if (run !== monitorPollRun || !shouldPollMonitor.value) return
  if (activeMonitor.value === 'traffic') await loadTraffic()
  else if (activeMonitor.value === 'quality') await loadQuality()

  if (run !== monitorPollRun || !shouldPollMonitor.value) return
  monitorTimer = window.setTimeout(() => {
    void pollActiveMonitor(run)
  }, 30_000)
}

function syncMonitorPolling() {
  stopMonitorPolling()
  if (!shouldPollMonitor.value) return
  const run = monitorPollRun
  void pollActiveMonitor(run)
}

function handleDrawerClosed() {
  stopMonitorPolling()
  emit('closed')
}

function handleDocumentVisibilityChange() {
  documentIsVisible.value = document.visibilityState !== 'hidden'
  syncMonitorPolling()
}

function handleNarrowViewportChange(event) {
  narrowViewport.value = event.matches
}

watch(
  () => [props.modelValue, resourceId.value],
  async ([open]) => {
    stopMonitorPolling()
    if (!open || !props.service) return

    const openedResourceKey = `${props.service?.service_type || ''}:${resourceId.value || ''}`
    if (lastOpenedResourceKey !== openedResourceKey) {
      tab.value = 'overview'
      trafficData.value = null
      qualityData.value = null
      trafficError.value = ''
      qualityError.value = ''
      resetTrafficRangeState()
      resetWizard()
      newUsername.value = ''
      reinstallForm.os_image = null
      reinstallForm.username = ''
      reinstallForm.password = ''
    }
    lastOpenedResourceKey = openedResourceKey
    newPassword.value = ''
    await reload()
    syncMonitorPolling()
  },
  { immediate: true },
)

watch(tab, () => {
  syncMonitorPolling()
})

watch(monitorHours, () => {
  if (tab.value === 'traffic' && trafficRangeMode.value === 'preset') {
    trafficData.value = null
    trafficError.value = ''
    syncMonitorPolling()
  } else if (tab.value === 'quality') {
    qualityData.value = null
    qualityError.value = ''
    syncMonitorPolling()
  }
})

watch(trafficRangeMode, (mode) => {
  if (mode === 'custom') {
    if (!Array.isArray(trafficCustomRange.value) || trafficCustomRange.value.length !== 2) {
      trafficCustomRange.value = appliedTrafficRange.value?.length === 2
        ? [...appliedTrafficRange.value]
        : buildPresetTrafficRange()
    }
    // 自定义模式下需点击「查询」后才拉取；先停掉快捷范围轮询
    stopMonitorPolling()
    return
  }
  appliedTrafficRange.value = null
  if (tab.value === 'traffic') {
    trafficData.value = null
    trafficError.value = ''
    syncMonitorPolling()
  }
})

onMounted(() => {
  narrowViewportQuery = window.matchMedia('(max-width: 860px)')
  handleNarrowViewportChange(narrowViewportQuery)
  narrowViewportQuery.addEventListener('change', handleNarrowViewportChange)
  document.addEventListener('visibilitychange', handleDocumentVisibilityChange)
  syncMonitorPolling()
})

onBeforeUnmount(() => {
  stopMonitorPolling()
  narrowViewportQuery?.removeEventListener('change', handleNarrowViewportChange)
  document.removeEventListener('visibilitychange', handleDocumentVisibilityChange)
})

async function loadSelfService() {
  if (!resourceId.value || !isVps.value) return
  snapLoading.value = true
  try {
    const [imagesRes, snapRes, jobsRes] = await Promise.all([
      getOsImages().catch(() => ({ data: [] })),
      getVPSSnapshots(resourceId.value).catch(() => ({ data: [] })),
      getVPSSelfServiceJobs(resourceId.value).catch(() => ({ data: [] })),
    ])
    osImages.value = imagesRes.data || imagesRes.results || []
    snapshots.value = snapRes.data || []
    selfJobs.value = jobsRes.data || []
  } finally {
    snapLoading.value = false
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function isVpsPoweredOn(status) {
  return ['running', 'paused', 'suspended'].includes(String(status || '').toLowerCase())
}

function unwrapVpsPayload(payload) {
  if (!payload) return null
  if (payload.id && (payload.vps_no || payload.status)) return payload
  return payload.data?.vps || payload.vps || payload.data || null
}

async function refreshVpsPowerStatus() {
  try {
    const res = await syncVPSNow(resourceId.value)
    const vps = unwrapVpsPayload(res) || unwrapVpsPayload(res?.data)
    if (vps) resourceDetail.value = { ...resourceDetail.value, ...vps }
  } catch {
    try {
      const detail = await getMyVPSDetail(resourceId.value)
      const vps = unwrapVpsPayload(detail) || detail
      if (vps?.id) resourceDetail.value = vps
    } catch { /* 用抽屉里已有状态继续判断 */ }
  }
  return String(resourceDetail.value?.status || '').toLowerCase()
}

async function waitUntilVpsStopped(timeoutMs = 90000, intervalMs = 2000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const status = await refreshVpsPowerStatus()
    if (status && !isVpsPoweredOn(status)) return true
    await sleep(intervalMs)
  }
  const latest = String(resourceDetail.value?.status || '').toLowerCase()
  return Boolean(latest) && !isVpsPoweredOn(latest)
}

async function ensureStoppedBeforeReinstall() {
  reinstallHint.value = '正在检查虚机状态…'
  const status = await refreshVpsPowerStatus()
  if (!isVpsPoweredOn(status)) return
  reinstallHint.value = '虚机运行中，正在关机…'
  await vpsPower(resourceId.value, 'shutdown')
  if (await waitUntilVpsStopped(90000)) return
  reinstallHint.value = '优雅关机超时，正在强制停止…'
  await vpsPower(resourceId.value, 'stop')
  if (await waitUntilVpsStopped(45000)) return
  throw new Error('关机未完成，已取消重装。请确认虚机已停止后重试。')
}

async function doReinstall() {
  if (!reinstallForm.os_image) return ElMessage.warning('请选择系统镜像')
  const current = String(resourceDetail.value?.status || '').toLowerCase()
  const extra = isVpsPoweredOn(current) ? '当前虚机正在运行，将先关机再重装。' : ''
  await ElMessageBox.confirm(`确定重装该系统？进行中的数据将丢失。${extra}`, '重装系统', { type: 'warning' })
  acting.value = 'reinstall'
  reinstallHint.value = '准备重装…'
  try {
    await ensureStoppedBeforeReinstall()
    reinstallHint.value = '正在提交重装…'
    await reinstallVPS(resourceId.value, {
      os_image: reinstallForm.os_image,
      username: reinstallForm.username || undefined,
      password: reinstallForm.password || undefined,
    })
    ElMessage.success('重装任务已提交，完成后可继续管理')
    reinstallForm.password = ''
    await loadSelfService()
    emit('refresh')
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    if (!error?.response) ElMessage.error(error?.message || '提交失败')
  } finally {
    acting.value = ''
    reinstallHint.value = ''
  }
}

function goChangeService() {
  visible.value = false
  router.push({ name: 'services' })
}

function generateOpsPassword() {
  newPassword.value = randomPassword()
}

function generateReinstallPassword() {
  reinstallForm.password = randomPassword()
}

function randomPassword() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%'
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  let pwd = ''
  for (const byte of bytes) pwd += chars[byte % chars.length]
  return pwd
}

async function doCreateSnapshot() {
  await ElMessageBox.confirm('确认创建快照？骨架阶段仅提交任务，不会调用节点 snapshot。', '创建快照', { type: 'warning' })
  acting.value = 'snapshot'
  try {
    await createVPSSnapshot(resourceId.value, { name: snapshotName.value })
    ElMessage.success('快照任务已提交')
    snapshotName.value = ''
    await loadSelfService()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '提交失败')
  } finally {
    acting.value = ''
  }
}

async function doRestoreSnapshot(row) {
  await ElMessageBox.confirm(`恢复快照 ${row.name || row.snapshot_no}？骨架阶段仅提交任务。`, '恢复快照', { type: 'warning' })
  try {
    await restoreVPSSnapshot(resourceId.value, row.id)
    ElMessage.success('恢复任务已提交')
    await loadSelfService()
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || '提交失败')
  }
}

async function doDeleteSnapshot(row) {
  await ElMessageBox.confirm(`删除快照 ${row.snapshot_no}？`, '删除快照', { type: 'warning' })
  await deleteVPSSnapshot(resourceId.value, row.id)
  ElMessage.success('已删除')
  await loadSelfService()
}

async function doPower(action) {
  const labels = { start: '启动', shutdown: '关机', restart: '重启', stop: '强制停止' }
  await ElMessageBox.confirm(`确定执行【${labels[action] || action}】？`, '电源操作', { type: 'warning' })
  acting.value = action
  try {
    await vpsPower(resourceId.value, action)
    ElMessage.success('操作已提交')
    await reload()
    emit('refresh')
  } finally {
    acting.value = ''
  }
}

function openConsole() {
  const r = router.resolve({ name: 'vps-vnc', params: { id: resourceId.value } })
  window.open(r.href, '_blank')
}

async function doSync() {
  acting.value = 'sync'
  try {
    const res = await syncVPSNow(resourceId.value)
    resourceDetail.value = res.data?.vps || resourceDetail.value
    ElMessage.success('同步成功')
  } finally {
    acting.value = ''
  }
}

async function doSetPassword() {
  if ((newPassword.value || '').length < 8) {
    ElMessage.warning('密码至少 8 位')
    return
  }
  await ElMessageBox.confirm('确认将新密码下发到虚拟机？节点未连通时仅写入档案。', '修改登录密码', { type: 'warning' })
  acting.value = 'pwd'
  try {
    const res = await setVPSRootPassword(resourceId.value, {
      password: newPassword.value,
      username: newUsername.value || undefined,
    })
    const applied = res?.data?.node_applied
    ElMessage.success(applied ? '密码已下发到虚拟机' : '密码已写入档案，节点暂未连通，开通或同步后将再下发')
    newPassword.value = ''
    await reload()
  } finally {
    acting.value = ''
  }
}

async function genWgKey() {
  acting.value = 'wgkey'
  try {
    const res = await edgeWgGenkey(resourceId.value)
    edgeForm.private_key = res.data?.private || ''
    edgeForm.public_key = res.data?.public || ''
    ElMessage.success('密钥已生成')
  } finally {
    acting.value = ''
  }
}

function resetWizard() {
  wizardStep.value = 0
  configSaved.value = false
  pushSucceeded.value = false
  pushResultText.value = ''
  initPushProgress()
}

function initPushProgress() {
  pushProgress.value = [
    { key: 'save', label: '保存协议配置', status: 'wait', detail: '' },
    { key: 'customers', label: '客户档案写入节点', status: 'wait', detail: '' },
    { key: 'interface', label: '公网对接接口配置完成', status: 'wait', detail: '' },
    { key: 'route', label: '业务路由配置完成', status: 'wait', detail: '' },
    { key: 'activate', label: '服务生效', status: 'wait', detail: '' },
  ]
}

function setPushStep(key, status, detail) {
  const row = pushProgress.value.find((item) => item.key === key)
  if (!row) return
  row.status = status
  if (detail != null) row.detail = detail
}

const wizardReviewRows = computed(() => {
  const proto = resourceDetail.value?.protocol || selectedProtocol.value
  if (proto === 'gre') {
    return [
      { label: '协议', value: 'GRE' },
      { label: '本端 IP', value: edgeForm.local_ip },
      { label: '远端 IP', value: edgeForm.remote_ip },
      { label: '隧道 IP/CIDR', value: edgeForm.tunnel_ip },
    ]
  }
  if (proto === 'wireguard') {
    return [
      { label: '协议', value: 'WireGuard' },
      { label: '接口 IP', value: edgeForm.interface_ip },
      { label: '监听端口', value: edgeForm.listen_port },
      { label: '对端公钥', value: edgeForm.peer_public_key },
      { label: '对端 Endpoint', value: edgeForm.peer_endpoint },
    ]
  }
  return [
    { label: '协议', value: proto || '—' },
    { label: '监听', value: `${edgeForm.listen_ip || ''} : ${edgeForm.listen_port || ''}` },
  ]
})

async function validateWizardForm() {
  const proto = resourceDetail.value?.protocol || selectedProtocol.value
  if (proto === 'gre') return validateGreForm()
  if (proto === 'wireguard') {
    const peer = String(edgeForm.peer_public_key || '').trim()
    const own = String(edgeForm.public_key || resourceDetail.value?.wg_config?.public_key || '').trim()
    if (!peer) {
      ElMessage.warning('请填写对端公钥')
      return false
    }
    if (own && peer === own) {
      ElMessage.error('对端公钥不能与本端公钥相同，请填写您侧 WireGuard 的公钥')
      return false
    }
  }
  return true
}

async function wizardNext() {
  if (wizardStep.value === 0) {
    if (!selectedProtocol.value || !switchableProtocols.value.includes(selectedProtocol.value)) {
      ElMessage.warning('请选择 GRE 或 WireGuard')
      return
    }
    const switched = await applyProtocolChoice()
    if (!switched) return
    wizardStep.value = 1
    return
  }
  if (wizardStep.value === 1) {
    if (!(await validateWizardForm())) return
    configSaved.value = false
    wizardStep.value = 2
  }
}

function wizardBack() {
  if (wizardStep.value <= 0 || pushSucceeded.value) return
  wizardStep.value -= 1
}

async function wizardSave() {
  if (!(await validateWizardForm())) return
  const ok = await saveEdgeConfig()
  if (!ok) return
  configSaved.value = true
  if (resourceDetail.value?.protocol === 'socks5') {
    wizardStep.value = 3
    pushSucceeded.value = true
    emit('refresh')
    return
  }
  wizardStep.value = 3
  initPushProgress()
  setPushStep('save', 'done', '配置已写入档案')
}

async function wizardPush() {
  if (!(await validateWizardForm())) return
  acting.value = 'push'
  pushSucceeded.value = false
  initPushProgress()
  try {
    setPushStep('save', 'running')
    const saved = await updateEdgeProtocolConfig(resourceId.value, buildEdgePayload())
    resourceDetail.value = saved.data || saved
    fillEdgeForm(resourceDetail.value)
    configSaved.value = true
    setPushStep('save', 'done', '配置已写入档案')

    setPushStep('customers', 'running', '正在写入节点…')
    const res = await pushEdgeToNode(resourceId.value, false)
    const data = res?.data || {}
    const serverSteps = data.progress_steps || []
    if (serverSteps.length) {
      for (const step of serverSteps) {
        setPushStep(step.key, step.status || 'done', step.detail || '')
      }
      if (!pushProgress.value.find((s) => s.key === 'save' && s.status === 'done')) {
        setPushStep('save', 'done', '配置已写入档案')
      }
    } else {
      const et = data.summary?.edge_tunnels || {}
      setPushStep('customers', 'done', '客户档案已同步')
      setPushStep(
        'interface',
        'done',
        et.created || et.reconfigured
          ? `接口已更新（新建 ${et.created || 0} / 重配置 ${et.reconfigured || 0}）`
          : '接口配置已核对',
      )
      const finalized = data.finalize || {}
      setPushStep(
        'route',
        finalized.route_errors?.length ? 'error' : 'done',
        finalized.route_pushed
          ? `已下发 ${finalized.route_pushed} 条 /32 路由`
          : '路由已核对',
      )
      setPushStep('activate', 'done', res?.message || '服务已生效')
    }
    pushResultText.value = res?.message || '已写入节点并生效'
    pushSucceeded.value = true
    emit('refresh')
    await reload()
    ElMessage.success(pushResultText.value)
  } catch (error) {
    const failed = pushProgress.value.find((s) => s.status === 'running')
    if (failed) {
      setPushStep(failed.key, 'error', error?.response?.data?.message || error?.message || '失败')
    }
  } finally {
    acting.value = ''
  }
}

function finishWizard() {
  tab.value = 'overview'
  emit('refresh')
}

function buildEdgePayload() {
  const payload = { ...edgeForm, protocol: resourceDetail.value?.protocol || selectedProtocol.value }
  if (!payload.password) delete payload.password
  if (!payload.private_key) delete payload.private_key
  // GRE Key / TTL 已取消，统一采用系统默认值
  if (resourceDetail.value?.protocol === 'gre') {
    payload.key = ''
    payload.ttl = null
  }
  return payload
}

async function saveEdgeConfig() {
  if (!(await validateGreForm())) return false
  acting.value = 'save'
  try {
    const res = await updateEdgeProtocolConfig(resourceId.value, buildEdgePayload())
    resourceDetail.value = res.data || res
    fillEdgeForm(resourceDetail.value)
    ElMessage.success('配置已保存')
    return true
  } catch (e) {
    // 错误消息由响应拦截器统一提示（含 IP 冲突 / 重复配置）
    return false
  } finally {
    acting.value = ''
  }
}

async function pushEdge() {
  if (!(await validateGreForm())) return
  acting.value = 'push'
  try {
    const outcome = await confirmPortalEdgePush(resourceId.value)
    if (outcome.ok || outcome.stage === 'push') await reload()
  } finally {
    acting.value = ''
  }
}

// 保存并实时下发：一步完成「修改 → 保存 → 下发到节点生效」
async function saveAndPush() {
  if (!(await validateGreForm())) return
  await ElMessageBox.confirm(
    '将先保存当前修改，再预览节点下发计划；确认后才会写入节点。若修改了隧道 IP，节点会同步更新对应路由下一跳。',
    '保存并下发',
    { type: 'warning' },
  )
  acting.value = 'savepush'
  try {
    const saved = await updateEdgeProtocolConfig(resourceId.value, buildEdgePayload())
    resourceDetail.value = saved.data || saved
    fillEdgeForm(resourceDetail.value)
    const outcome = await confirmPortalEdgePush(resourceId.value)
    if (outcome.ok) {
      // 成功文案由 confirmPortalEdgePush 给出
    }
    if (outcome.ok || outcome.stage === 'push') await reload()
  } catch (e) {
    // 错误消息由响应拦截器统一提示（保存冲突 / 下发未完全生效）
  } finally {
    acting.value = ''
  }
}
</script>

<style scoped>
.dh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.dh-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.dh-no {
  font-family: monospace;
  color: var(--ce-muted);
}
.dh-name {
  font-weight: 700;
  font-size: 16px;
}
.sub-title {
  font-weight: 700;
  margin-bottom: 8px;
  font-size: 14px;
}
.mono {
  font-family: monospace;
}
.table-scroll {
  width: 100%;
  overflow-x: auto;
  overflow-y: hidden;
}
.table-scroll:focus-visible {
  outline: 2px solid var(--ce-primary);
  outline-offset: 2px;
}
.ip-table {
  min-width: 640px;
}
.checklist,
.client-guide {
  margin-bottom: 16px;
}
.client-guide ul {
  margin: 0;
  padding-left: 18px;
  color: var(--ce-text, #303133);
  font-size: 13px;
  line-height: 1.7;
}
.interfaces-table {
  min-width: 560px;
}
.ops-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.pwd-row {
  display: flex;
  gap: 8px;
  width: 100%;
}
.pwd-row .el-input {
  flex: 1;
}
.edge-actions {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}
.config-steps {
  margin: 4px 0 18px;
}
.wizard-pane {
  min-height: 120px;
}
.wizard-alert {
  margin: 12px 0;
}
.review-desc {
  max-width: 640px;
}
.push-steps {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}
.push-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ce-border, #ebeef5);
  border-radius: 8px;
  font-size: 13px;
}
.push-step.done {
  border-color: #b3e19d;
  background: #f0f9eb;
}
.push-step.error {
  border-color: #fab6b6;
  background: #fef0f0;
}
.push-step.running {
  border-color: #b3d8ff;
  background: #ecf5ff;
}
.push-step.warn {
  border-color: #f3d19e;
  background: #fdf6ec;
}
.push-label {
  font-weight: 600;
}
.push-detail {
  color: var(--ce-muted, #909399);
  margin-top: 2px;
}
.cfg-note p {
  margin: 2px 0;
  line-height: 1.6;
  font-size: 13px;
}
.field-tip {
  font-size: 12px;
  color: var(--ce-muted, #909399);
  line-height: 1.4;
  margin-top: 2px;
}
.proto-picker {
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--ce-border, #ebeef5);
}
.proto-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.monitor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.monitor-toolbar-left {
  display: flex;
  min-width: 0;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.monitor-range-label {
  color: var(--ce-text-secondary);
  font-size: 13px;
  white-space: nowrap;
}
.monitor-range {
  width: 116px;
}
.monitor-datetime {
  width: min(360px, 100%);
}
.monitor-updated {
  color: var(--ce-muted);
  font-size: 12px;
  white-space: nowrap;
}
.monitor-error {
  margin-bottom: 12px;
}
@media (max-width: 860px) {
  .dh {
    align-items: flex-start;
    gap: 10px;
  }
  .dh-name {
    font-size: 14px;
  }
  .edge-actions {
    flex-wrap: wrap;
  }
  .monitor-toolbar {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .monitor-updated {
    white-space: normal;
  }
  :deep(.el-form-item__label) {
    width: auto !important;
    justify-content: flex-start;
  }
  :deep(.el-form-item__content) {
    margin-left: 0 !important;
  }
}
</style>
