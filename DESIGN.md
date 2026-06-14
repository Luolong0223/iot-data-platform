# IoT Data Platform - 设计规范 v2.0

## 1. 设计理念

### 核心原则
- **工业级专业感**：深色主题为主，强调数据可视化
- **高效信息密度**：合理利用空间，减少滚动
- **实时数据优先**：突出显示关键指标和告警
- **操作便捷性**：减少点击次数，提高效率

### 目标用户
- 工业监控工程师
- 设备运维人员
- 数据分析师
- 系统管理员

## 2. Design Tokens

### 色彩系统

#### 主色调 (Primary)
```css
--color-primary: #3B82F6;        /* 主蓝色 */
--color-primary-light: #60A5FA;   /* 浅蓝 */
--color-primary-dark: #2563EB;    /* 深蓝 */
--color-primary-bg: #EFF6FF;      /* 蓝色背景 */
```

#### 功能色
```css
--color-success: #10B981;         /* 成功/在线 */
--color-warning: #F59E0B;         /* 警告/待处理 */
--color-danger: #EF4444;          /* 错误/离线/严重告警 */
--color-info: #06B6D4;            /* 信息 */

/* 渐变 */
--gradient-primary: linear-gradient(135deg, #3B82F6, #8B5CF6);
--gradient-success: linear-gradient(135deg, #10B981, #059669);
--gradient-warning: linear-gradient(135deg, #F59E0B, #F97316);
```

#### 中性色
```css
--color-bg-primary: #0F172A;      /* 主背景 - 深色 */
--color-bg-secondary: #1E293B;    /* 次级背景 */
--color-bg-tertiary: #334155;     /* 三级背景 */
--color-border: #475569;           /* 边框 */
--color-text-primary: #F8FAFC;    /* 主文字 */
--color-text-secondary: #94A3B8;   /* 次级文字 */
--color-text-muted: #64748B;       /* 弱化文字 */
```

### 字体系统
```css
--font-family: 'Inter', 'SF Pro Display', -apple-system, BlinkMacSystemFont, sans-serif;
--font-mono: 'JetBrains Mono', 'Fira Code', monospace;

/* 字号 */
--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */

/* 字重 */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;

/* 行高 */
--leading-tight: 1.25;
--leading-normal: 1.5;
--leading-relaxed: 1.75;
```

### 间距系统
```css
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-5: 1.25rem;   /* 20px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-10: 2.5rem;   /* 40px */
--space-12: 3rem;     /* 48px */
```

### 圆角
```css
--radius-sm: 0.375rem;   /* 6px */
--radius-md: 0.5rem;     /* 8px */
--radius-lg: 0.75rem;    /* 12px */
--radius-xl: 1rem;       /* 16px */
--radius-full: 9999px;   /* 圆形 */
```

### 阴影
```css
--shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
--shadow-glow: 0 0 20px rgba(59, 130, 246, 0.3);  /* 发光效果 */
```

### 动画
```css
--duration-fast: 150ms;
--duration-normal: 250ms;
--duration-slow: 350ms;
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

## 3. 布局结构

### 整体布局
```
┌─────────────────────────────────────────────────────────┐
│                    顶部导航栏 (56px)                      │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  侧边栏   │              内容区域                        │
│ (240px)   │                                              │
│          │                                              │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### 侧边栏结构
- Logo区域 (64px)
- 导航菜单 (可折叠)
- 用户信息区 (底部固定)

### 顶部导航栏
- 面包屑导航
- 搜索框
- 通知铃铛
- 用户头像下拉菜单

## 4. 组件规范

### 卡片组件
```css
.card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
}

.card-header {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}
```

### 表格组件
```css
.table {
  width: 100%;
  border-collapse: collapse;
}

.table th {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  padding: var(--space-3) var(--space-4);
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-primary);
}
```

### 按钮组件
```css
.btn-primary {
  background: var(--gradient-primary);
  border: none;
  color: white;
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  transition: all var(--duration-fast) var(--ease-default);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-glow);
}
```

### 状态指示器
```css
.status-online { color: var(--color-success); }
.status-offline { color: var(--color-danger); }
.status-warning { color: var(--color-warning); }

.dot-online { background: var(--color-success); box-shadow: 0 0 8px var(--color-success); }
.dot-offline { background: var(--color-danger); }
.dot-warning { background: var(--color-warning); }
```

## 5. 页面特定规范

### 仪表盘页面
- 4个统计卡片（设备总数、在线数、告警数、数据点）
- 实时趋势图（最近24小时）
- 最近告警列表
- 快捷操作面板

### 设备管理页面
- 设备列表表格（支持排序、筛选）
- 设备状态徽章
- 批量操作按钮
- 分页控件

### 数据查看页面
- 时间范围选择器
- 设备筛选器
- 数据表格 + 图表切换
- 导出功能

### 告警管理页面
- 实时告警流（WebSocket）
- 告警级别筛选
- 告警统计图表
- 处理状态标记

## 6. 图标系统

使用 Bootstrap Icons 或 Lucide Icons：
- 统一使用 24x24 尺寸
- 保持一致的线条粗细
- 支持动态颜色变化

## 7. 响应式断点

```css
/* 移动端 */
@media (max-width: 767px) {
  --sidebar-width: 0;
  .sidebar { transform: translateX(-100%); }
}

/* 平板 */
@media (min-width: 768px) and (max-width: 1023px) {
  --sidebar-width: 200px;
}

/* 桌面端 */
@media (min-width: 1024px) {
  --sidebar-width: 240px;
}
```
