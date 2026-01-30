import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="app-layout">
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="brand-icon">
            <i class="fa fa-chart-line"></i>
          </div>
          <span class="brand-text">MT5</span>
        </div>
        <nav class="sidebar-nav">
          <a routerLink="/accounts" routerLinkActive="active" class="nav-item">
            <i class="fa fa-signal"></i>
            <span>Signaux</span>
          </a>
          <a routerLink="/portfolios" routerLinkActive="active" class="nav-item">
            <i class="fa fa-briefcase"></i>
            <span>Portfolios</span>
          </a>
        </nav>
        <div class="sidebar-footer">
          <div class="status-indicator online">
            <span class="dot"></span>
            <span class="text">En ligne</span>
          </div>
        </div>
      </aside>
      <main class="main-content">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      min-height: 100vh;
      background: #0a0a0a;
    }

    .sidebar {
      width: 200px;
      background: #0d0d0d;
      border-right: 1px solid #1a1a1a;
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0;
      left: 0;
      bottom: 0;
      z-index: 100;
    }

    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px;
      border-bottom: 1px solid #1a1a1a;
    }

    .brand-icon {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #2962ff, #1e88e5);
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .brand-icon i {
      color: #fff;
      font-size: 16px;
    }

    .brand-text {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }

    .sidebar-nav {
      flex: 1;
      padding: 16px 12px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 8px;
      text-decoration: none;
      color: #888;
      font-size: 13px;
      font-weight: 500;
      transition: all 0.2s;
    }

    .nav-item i {
      font-size: 16px;
      width: 20px;
      text-align: center;
    }

    .nav-item:hover {
      color: #e8e8e8;
      background: rgba(255,255,255,0.05);
    }

    .nav-item.active {
      color: #fff;
      background: linear-gradient(135deg, rgba(41,98,255,0.2), rgba(41,98,255,0.1));
      border-left: 3px solid #2962ff;
      margin-left: -3px;
    }

    .sidebar-footer {
      padding: 16px 20px;
      border-top: 1px solid #1a1a1a;
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
      border-radius: 50%;
      background: #666;
    }

    .status-indicator.online .dot {
      background: #00c853;
      box-shadow: 0 0 8px rgba(0,200,83,0.5);
    }

    .status-indicator.online .text {
      color: #00c853;
    }

    .main-content {
      flex: 1;
      margin-left: 200px;
      min-height: 100vh;
    }

    @media (max-width: 768px) {
      .sidebar {
        width: 60px;
      }
      .brand-text, .nav-item span, .status-indicator .text {
        display: none;
      }
      .sidebar-brand {
        justify-content: center;
        padding: 16px;
      }
      .nav-item {
        justify-content: center;
        padding: 14px;
      }
      .main-content {
        margin-left: 60px;
      }
    }
  `]
})
export class App {}
