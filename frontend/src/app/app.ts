import { Component, inject, signal, computed, OnInit, OnDestroy } from '@angular/core';
import { Router, NavigationEnd, RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { StorageService, FirmStateService, ConnectionStateService } from './core';
import { AccountsApiService } from './data-access';
import { Subscription, filter } from 'rxjs';
import packageJson from '../../package.json';

interface NavItem {
  icon: string;
  label: string;
  route: string | null;
  badge?: () => number | null;
  section: string;
  requiresFirm?: boolean;
  requiresNoFirm?: boolean;
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
          <div class="brand-logo">
            <span class="logo-letter">E</span>
          </div>
          @if (!collapsed()) {
            <div class="brand-title">
              <span class="brand-text">Elite<span class="brand-highlight">Monitor</span></span>
              <span class="brand-tagline">Trading Intelligence</span>
            </div>
          }
        </div>

        <!-- Firm Selector -->
        <div class="firm-selector">
          @if (!collapsed()) {
            <div class="firm-dropdown" (click)="toggleFirmDropdown()">
              <i class="fa-solid fa-building firm-dropdown-icon"></i>
              <span class="firm-dropdown-label">{{ selectedFirmLabel() }}</span>
              <i class="fa-solid fa-chevron-down firm-dropdown-arrow" [class.open]="firmDropdownOpen()"></i>
            </div>
            @if (firmDropdownOpen()) {
              <div class="firm-dropdown-menu">
                <div class="firm-option" [class.active]="firmState.selectedFirmId() === null" (click)="onSelectFirm(null)">
                  <i class="fa-solid fa-globe"></i> Toutes les firms
                </div>
                @for (firm of firmState.firms(); track firm.id) {
                  <div class="firm-option" [class.active]="firmState.selectedFirmId() === firm.id" (click)="onSelectFirm(firm.id)">
                    <i class="fa-solid fa-building"></i> {{ firm.name }}
                  </div>
                }
                <div class="firm-option-divider"></div>
                <div class="firm-option manage" (click)="goToFirms()">
                  <i class="fa-solid fa-cog"></i> Gérer les firms
                </div>
              </div>
            }
          } @else {
            <div class="firm-badge" [attr.title]="selectedFirmLabel()" (click)="toggleFirmDropdown()">
              {{ firmInitial() }}
            </div>
            @if (firmDropdownOpen()) {
              <div class="firm-dropdown-menu collapsed-menu">
                <div class="firm-option" [class.active]="firmState.selectedFirmId() === null" (click)="onSelectFirm(null)">
                  <i class="fa-solid fa-globe"></i> Toutes les firms
                </div>
                @for (firm of firmState.firms(); track firm.id) {
                  <div class="firm-option" [class.active]="firmState.selectedFirmId() === firm.id" (click)="onSelectFirm(firm.id)">
                    <i class="fa-solid fa-building"></i> {{ firm.name }}
                  </div>
                }
                <div class="firm-option-divider"></div>
                <div class="firm-option manage" (click)="goToFirms()">
                  <i class="fa-solid fa-cog"></i> Gérer les firms
                </div>
              </div>
            }
          }
        </div>

        <!-- Navigation -->
        <nav class="sidebar-nav">
          @for (section of sections; track section) {
            @if (getItemsBySection(section).length > 0) {
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
          }
        </nav>

        <!-- Footer -->
        <div class="sidebar-footer">
          <div class="status-indicator" [class.online]="connectionState.backendOnline()" [class.offline]="!connectionState.backendOnline()">
            <span class="dot"></span>
            @if (!collapsed()) {
              <span class="status-text">{{ connectionState.backendOnline() ? 'En ligne' : 'Hors ligne' }}</span>
            }
          </div>
          @if (!collapsed()) {
            <span class="version">v{{ appVersion }}</span>
          }
        </div>

      </aside>
      <main class="main-content" [class.collapsed]="collapsed()">
        @if (!connectionState.backendOnline()) {
          <div class="backend-banner">
            <i class="fa-solid fa-exclamation-triangle"></i>
            Backend indisponible — Vérifiez que le serveur est démarré
          </div>
        }
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

    .brand-logo {
      width: 36px;
      height: 36px;
      min-width: 36px;
      background: linear-gradient(135deg, #1a3a8f, var(--accent), #00e5ff);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 2px 16px rgba(41, 98, 255, 0.4), inset 0 1px 0 rgba(255,255,255,0.1);
    }

    .logo-letter {
      font-size: 20px;
      font-weight: 900;
      color: #fff;
      font-family: 'Inter', 'Segoe UI', sans-serif;
      letter-spacing: -1px;
      text-shadow: 0 1px 4px rgba(0,0,0,0.3);
      line-height: 1;
    }

    .brand-title {
      display: flex;
      flex-direction: column;
      gap: 1px;
      opacity: 1;
      transition: opacity calc(var(--transition-speed) * 0.6) ease;
    }

    .sidebar.collapsed .brand-title {
      opacity: 0;
    }

    .brand-text {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-primary);
      white-space: nowrap;
      letter-spacing: -0.3px;
    }

    .brand-highlight {
      color: var(--accent);
      font-weight: 600;
    }

    .brand-tagline {
      font-size: 9px;
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: var(--text-muted);
      white-space: nowrap;
    }

    /* ==================== FIRM SELECTOR ==================== */
    .firm-selector {
      padding: 8px;
      border-bottom: 1px solid var(--border-color);
      position: relative;
    }

    .firm-dropdown {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 8px;
      cursor: pointer;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--border-color);
      transition: all 0.2s ease;
    }

    .firm-dropdown:hover {
      background: rgba(255, 255, 255, 0.07);
      border-color: rgba(255, 255, 255, 0.1);
    }

    .firm-dropdown-icon {
      font-size: 12px;
      color: var(--accent);
      min-width: 14px;
      text-align: center;
    }

    .firm-dropdown-label {
      flex: 1;
      font-size: 12px;
      font-weight: 500;
      color: var(--text-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .firm-dropdown-arrow {
      font-size: 10px;
      color: var(--text-muted);
      transition: transform 0.2s ease;
    }

    .firm-dropdown-arrow.open {
      transform: rotate(180deg);
    }

    .firm-dropdown-menu {
      position: absolute;
      top: 100%;
      left: 8px;
      right: 8px;
      background: #141414;
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 4px;
      z-index: 200;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
      margin-top: 4px;
    }

    .firm-option {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      color: var(--text-secondary);
      transition: all 0.15s ease;
    }

    .firm-option:hover {
      background: rgba(255, 255, 255, 0.06);
      color: var(--text-primary);
    }

    .firm-option.active {
      background: rgba(41, 98, 255, 0.15);
      color: var(--accent);
    }

    .firm-option i {
      font-size: 11px;
      width: 14px;
      text-align: center;
    }

    .firm-option-divider {
      height: 1px;
      background: var(--border-color);
      margin: 4px 0;
    }

    .firm-option.manage {
      color: var(--text-muted);
      font-size: 11px;
    }

    .firm-option.manage:hover {
      color: var(--accent);
    }

    .firm-badge {
      width: 36px;
      height: 36px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(41, 98, 255, 0.15);
      color: var(--accent);
      border-radius: 8px;
      font-size: 14px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s ease;
    }

    .firm-badge:hover {
      background: rgba(41, 98, 255, 0.25);
    }

    .collapsed-menu {
      position: fixed;
      left: var(--sidebar-collapsed-width);
      top: auto;
      right: auto;
      width: 200px;
      margin-top: -40px;
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

    .status-indicator.offline .dot {
      background: #ff1744;
      box-shadow: 0 0 8px rgba(255, 23, 68, 0.5);
    }

    .status-indicator.offline .status-text {
      color: #ff1744;
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

    /* ==================== BACKEND BANNER ==================== */
    .backend-banner {
      background: rgba(255, 23, 68, 0.12);
      border-bottom: 1px solid rgba(255, 23, 68, 0.3);
      color: #ff1744;
      padding: 10px 20px;
      font-size: 13px;
      font-weight: 500;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .backend-banner i {
      font-size: 14px;
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
      .brand-title, .nav-label, .status-text, .section-label, .badge, .version {
        display: none !important;
      }
      .firm-dropdown, .firm-dropdown-menu {
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
  private readonly router = inject(Router);
  readonly firmState = inject(FirmStateService);
  readonly connectionState = inject(ConnectionStateService);
  private sub?: Subscription;
  private routerSub?: Subscription;

  private readonly COLLAPSED_KEY = 'sidebar_collapsed';

  readonly appVersion = packageJson.version;
  collapsed = signal(false);
  private allAccounts = signal<{connected: boolean; client: string | null}[]>([]);
  firmDropdownOpen = signal(false);

  connectedCount = computed(() => {
    const profileNames = this.firmState.profileNames();
    const accounts = this.allAccounts();
    if (accounts.length === 0) return null;
    const filtered = accounts.filter(a =>
      a.connected && a.client !== null && profileNames.includes(a.client)
    );
    return filtered.length > 0 ? filtered.length : null;
  });

  selectedFirmLabel = computed(() => {
    const firm = this.firmState.selectedFirm();
    return firm ? firm.name : 'Toutes les firms';
  });

  firmInitial = computed(() => {
    const firm = this.firmState.selectedFirm();
    return firm ? firm.name.charAt(0).toUpperCase() : '*';
  });

  readonly sections = ['PRINCIPAL', 'GESTION'];

  navItems = computed<NavItem[]>(() => {
    const slug = this.firmState.selectedFirmSlug();
    const prefix = slug ? `/${slug}` : '';
    return [
      { icon: 'fa-th-large', label: 'Dashboard', route: '/dashboard', section: 'PRINCIPAL', requiresNoFirm: true },
      { icon: 'fa-chart-line', label: 'Comptes', route: `${prefix}/accounts`, badge: () => this.connectedCount(), section: 'PRINCIPAL', requiresFirm: true },
      { icon: 'fa-briefcase', label: 'Portifs', route: `${prefix}/portifs`, section: 'PRINCIPAL', requiresFirm: true },
      { icon: 'fa-cog', label: 'Paramètres', route: null, section: 'GESTION' },
    ];
  });

  ngOnInit(): void {
    this.collapsed.set(this.storage.get<boolean>(this.COLLAPSED_KEY, false));
    this.loadConnectedCount();

    // Sync firm selection from URL path
    this.routerSub = this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd)
    ).subscribe(e => {
      this.syncFirmFromUrl(e.urlAfterRedirects || e.url);
    });
    // Initial sync
    this.syncFirmFromUrl(this.router.url);
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
    this.routerSub?.unsubscribe();
  }

  toggleCollapse(): void {
    const next = !this.collapsed();
    this.collapsed.set(next);
    this.storage.set(this.COLLAPSED_KEY, next);
  }

  toggleFirmDropdown(): void {
    this.firmDropdownOpen.update(v => !v);
  }

  onSelectFirm(id: number | null): void {
    this.firmState.selectFirm(id);
    this.firmDropdownOpen.set(false);
    if (id === null) {
      this.router.navigate(['/dashboard']);
    } else {
      const firm = this.firmState.selectedFirm();
      if (firm) {
        this.router.navigate([`/${this.firmState.selectedFirmSlug()}/accounts`]);
      }
    }
  }

  goToFirms(): void {
    this.firmDropdownOpen.set(false);
    this.router.navigate(['/firms']);
  }

  private syncFirmFromUrl(url: string): void {
    const segments = url.split('?')[0].split('/').filter(Boolean);
    const firstSegment = segments[0];
    const reserved = ['dashboard', 'firms'];
    if (firstSegment && !reserved.includes(firstSegment)) {
      this.firmState.selectFirmBySlug(firstSegment);
    } else if (firstSegment === 'dashboard') {
      this.firmState.selectFirm(null);
    }
  }

  getItemsBySection(section: string): NavItem[] {
    const hasFirm = this.firmState.selectedFirmId() !== null;
    return this.navItems().filter(item => {
      if (item.section !== section) return false;
      if (item.requiresFirm && !hasFirm) return false;
      if (item.requiresNoFirm && hasFirm) return false;
      return true;
    });
  }

  private loadConnectedCount(): void {
    this.sub = this.accountsApi.getAccounts().subscribe({
      next: (accounts) => this.allAccounts.set(accounts),
      error: () => this.allAccounts.set([])
    });
  }
}
