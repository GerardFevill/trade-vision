import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { StorageService } from './core';
import { AccountsApiService } from './data-access';
import { Subscription } from 'rxjs';

interface NavItem {
  icon: string;
  label: string;
  route: string | null;
  badge?: () => number | null;
  section: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-layout">
      <aside class="sidebar" [class.collapsed]="collapsed()">

        <!-- Brand -->
        <div class="sidebar-brand" (click)="toggleCollapse()" [attr.title]="collapsed() ? 'Ouvrir le menu' : 'Réduire le menu'">
          <div class="brand-icon">
            <i class="fa fa-chart-line"></i>
          </div>
          @if (!collapsed()) {
            <span class="brand-text">Elite Monitor</span>
          }
        </div>

        <!-- Navigation -->
        <nav class="sidebar-nav">
          @for (section of sections; track section) {
            <div class="nav-section">
              @if (!collapsed()) {
                <span class="section-label">{{ section }}</span>
              } @else {
                <div class="section-divider"></div>
              }
              @for (item of getItemsBySection(section); track item.label) {
                @if (item.route) {
                  <a [routerLink]="item.route" routerLinkActive="active" class="nav-item"
                     [attr.title]="collapsed() ? item.label : null">
                    <i class="fa {{ item.icon }}"></i>
                    @if (!collapsed()) {
                      <span class="nav-label">{{ item.label }}</span>
                      @if (item.badge && item.badge() !== null) {
                        <span class="badge">{{ item.badge() }}</span>
                      }
                    }
                  </a>
                } @else {
                  <span class="nav-item disabled" [attr.title]="collapsed() ? item.label : null">
                    <i class="fa {{ item.icon }}"></i>
                    @if (!collapsed()) {
                      <span class="nav-label">{{ item.label }}</span>
                    }
                  </span>
                }
              }
            </div>
          }
        </nav>

        <!-- Footer -->
        <div class="sidebar-footer">
          <div class="status-indicator online">
            <span class="dot"></span>
            @if (!collapsed()) {
              <span class="status-text">En ligne</span>
            }
          </div>
          @if (!collapsed()) {
            <span class="version">v1.0.0</span>
          }
        </div>

      </aside>
      <main class="main-content" [class.collapsed]="collapsed()">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    :host {
      --sidebar-width: 220px;
      --sidebar-collapsed-width: 68px;
      --transition-speed: 0.3s;
      --bg-primary: #0a0a0a;
      --bg-sidebar: #0d0d0d;
      --border-color: #1a1a1a;
      --accent: #2962ff;
      --accent-hover: #1e88e5;
      --text-primary: #fff;
      --text-secondary: #888;
      --text-muted: #555;
      --success: #00c853;
    }

    .app-layout {
      display: flex;
      min-height: 100vh;
      background: var(--bg-primary);
    }

    /* ==================== SIDEBAR ==================== */
    .sidebar {
      width: var(--sidebar-width);
      background: var(--bg-sidebar);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      z-index: 100;
      transition: width var(--transition-speed) ease;
      overflow: hidden;
    }

    .sidebar.collapsed {
      width: var(--sidebar-collapsed-width);
    }

    /* ==================== BRAND ==================== */
    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      border-bottom: 1px solid var(--border-color);
      min-height: 64px;
      cursor: pointer;
      transition: background 0.2s ease;
    }

    .sidebar-brand:hover {
      background: rgba(255, 255, 255, 0.03);
    }

    .brand-icon {
      width: 36px;
      height: 36px;
      min-width: 36px;
      background: linear-gradient(135deg, var(--accent), var(--accent-hover));
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 12px rgba(41, 98, 255, 0.3);
    }

    .brand-icon i {
      color: var(--text-primary);
      font-size: 16px;
    }

    .brand-text {
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
      white-space: nowrap;
      opacity: 1;
      transition: opacity calc(var(--transition-speed) * 0.6) ease;
    }

    .sidebar.collapsed .brand-text {
      opacity: 0;
    }

    /* ==================== NAV ==================== */
    .sidebar-nav {
      flex: 1;
      padding: 12px 8px;
      display: flex;
      flex-direction: column;
      gap: 2px;
      overflow-y: auto;
      overflow-x: hidden;
    }

    .nav-section {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .nav-section + .nav-section {
      margin-top: 8px;
    }

    .section-label {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1.2px;
      color: var(--text-muted);
      padding: 8px 12px 4px;
      white-space: nowrap;
      opacity: 1;
      transition: opacity calc(var(--transition-speed) * 0.6) ease;
    }

    .sidebar.collapsed .section-label {
      opacity: 0;
    }

    .section-divider {
      height: 1px;
      background: var(--border-color);
      margin: 4px 12px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 8px;
      text-decoration: none;
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
      transition: all 0.2s ease;
      cursor: pointer;
      white-space: nowrap;
      position: relative;
      border-left: 3px solid transparent;
    }

    .nav-item i {
      font-size: 16px;
      width: 20px;
      min-width: 20px;
      text-align: center;
      transition: transform 0.2s ease;
    }

    .nav-label {
      opacity: 1;
      transition: opacity calc(var(--transition-speed) * 0.6) ease;
    }

    .sidebar.collapsed .nav-label {
      opacity: 0;
    }

    .nav-item:hover:not(.disabled) {
      color: #e0e0e0;
      background: rgba(255, 255, 255, 0.05);
      transform: translateX(2px);
    }

    .nav-item:hover:not(.disabled) i {
      transform: scale(1.1);
    }

    .nav-item.active {
      color: var(--text-primary);
      background: linear-gradient(135deg, rgba(41, 98, 255, 0.15), rgba(41, 98, 255, 0.05));
      border-left-color: var(--accent);
    }

    .nav-item.active i {
      color: var(--accent);
    }

    .nav-item.disabled {
      color: var(--text-muted);
      cursor: not-allowed;
      opacity: 0.5;
    }

    .sidebar.collapsed .nav-item {
      justify-content: center;
      padding: 12px;
      border-left-color: transparent;
    }

    .sidebar.collapsed .nav-item.active {
      background: rgba(41, 98, 255, 0.15);
    }

    .sidebar.collapsed .nav-item.active::after {
      content: '';
      position: absolute;
      left: 0;
      top: 25%;
      height: 50%;
      width: 3px;
      background: var(--accent);
      border-radius: 0 2px 2px 0;
    }

    /* Badge */
    .badge {
      margin-left: auto;
      background: rgba(41, 98, 255, 0.2);
      color: var(--accent);
      font-size: 11px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 10px;
      min-width: 20px;
      text-align: center;
      transition: opacity calc(var(--transition-speed) * 0.6) ease;
    }

    .sidebar.collapsed .badge {
      opacity: 0;
      position: absolute;
    }

    /* ==================== FOOTER ==================== */
    .sidebar-footer {
      padding: 14px 16px;
      border-top: 1px solid var(--border-color);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }

    .sidebar.collapsed .sidebar-footer {
      justify-content: center;
      padding: 14px 8px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: #666;
    }

    .status-indicator .dot {
      width: 8px;
      height: 8px;
      min-width: 8px;
      border-radius: 50%;
      background: #666;
    }

    .status-indicator.online .dot {
      background: var(--success);
      box-shadow: 0 0 8px rgba(0, 200, 83, 0.5);
      animation: pulse 2s ease-in-out infinite;
    }

    .status-indicator.online .status-text {
      color: var(--success);
      white-space: nowrap;
    }

    .version {
      font-size: 10px;
      color: var(--text-muted);
      white-space: nowrap;
    }

    @keyframes pulse {
      0%, 100% { box-shadow: 0 0 4px rgba(0, 200, 83, 0.3); }
      50% { box-shadow: 0 0 12px rgba(0, 200, 83, 0.6); }
    }

    /* ==================== MAIN CONTENT ==================== */
    .main-content {
      flex: 1;
      margin-left: var(--sidebar-width);
      min-height: 100vh;
      transition: margin-left var(--transition-speed) ease;
    }

    .main-content.collapsed {
      margin-left: var(--sidebar-collapsed-width);
    }

    /* ==================== RESPONSIVE ==================== */
    @media (max-width: 768px) {
      .sidebar {
        width: var(--sidebar-collapsed-width) !important;
      }
      .brand-text, .nav-label, .status-text, .section-label, .badge, .version {
        display: none !important;
      }
      .sidebar-brand {
        justify-content: center;
        padding: 16px;
      }
      .nav-item {
        justify-content: center;
        padding: 14px;
        border-left-color: transparent !important;
      }
      .nav-item.active::after {
        content: '';
        position: absolute;
        left: 0;
        top: 25%;
        height: 50%;
        width: 3px;
        background: var(--accent);
        border-radius: 0 2px 2px 0;
      }
      .main-content {
        margin-left: var(--sidebar-collapsed-width) !important;
      }
      .sidebar-footer {
        justify-content: center;
      }
      .section-divider {
        display: block !important;
      }
    }
  `]
})
export class App implements OnInit, OnDestroy {
  private readonly storage = inject(StorageService);
  private readonly accountsApi = inject(AccountsApiService);
  private sub?: Subscription;

  private readonly COLLAPSED_KEY = 'sidebar_collapsed';

  collapsed = signal(false);
  connectedCount = signal<number | null>(null);

  readonly sections = ['TRADING', 'SYSTÈME'];

  readonly navItems: NavItem[] = [
    { icon: 'fa-chart-line', label: 'Signaux', route: '/accounts', badge: () => this.connectedCount(), section: 'TRADING' },
    { icon: 'fa-briefcase', label: 'Portfolios', route: '/portfolios', section: 'TRADING' },
    { icon: 'fa-cog', label: 'Paramètres', route: null, section: 'SYSTÈME' },
  ];

  ngOnInit(): void {
    this.collapsed.set(this.storage.get<boolean>(this.COLLAPSED_KEY, false));
    this.loadConnectedCount();
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  toggleCollapse(): void {
    const next = !this.collapsed();
    this.collapsed.set(next);
    this.storage.set(this.COLLAPSED_KEY, next);
  }

  getItemsBySection(section: string): NavItem[] {
    return this.navItems.filter(item => item.section === section);
  }

  private loadConnectedCount(): void {
    this.sub = this.accountsApi.getAccounts().subscribe({
      next: (accounts) => {
        const count = accounts.filter(a => a.connected).length;
        this.connectedCount.set(count > 0 ? count : null);
      },
      error: () => this.connectedCount.set(null)
    });
  }
}
