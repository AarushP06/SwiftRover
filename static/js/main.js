// Main JavaScript for IoT Smart Robot Car

// SwiftRover Dashboard - Main JavaScript
// Glassy Blue Gradient Theme

// Chart Configuration
const CHART_COLORS = {
  primary: '#42a5f5',
  secondary: '#1e88e5',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  grid: 'rgba(66, 165, 245, 0.1)',
  text: '#b3d9ff',
  border: 'rgba(66, 165, 245, 0.2)',
};

// Configure Chart.js defaults for SwiftRover theme
Chart.defaults.color = CHART_COLORS.text;
Chart.defaults.borderColor = CHART_COLORS.border;
Chart.defaults.backgroundColor = CHART_COLORS.grid;
Chart.defaults.font.family = '"Inter", sans-serif';

// Utility functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function showStatus(message, success) {
    const statusEl = document.getElementById('status-message');
    if (statusEl) {
        statusEl.textContent = message;
        statusEl.className = `status-message ${success ? 'status-success' : 'status-error'}`;
        setTimeout(() => {
            statusEl.className = 'status-message';
            statusEl.textContent = '';
        }, 3000);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 SwiftRover Dashboard Loaded');
    console.log('UI Theme: Glassy Blue Gradient');
});

// Chart helper function
function createChart(ctx, type, data, options = {}) {
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
            legend: {
                labels: {
                    color: CHART_COLORS.text,
                    font: { family: '"Inter", sans-serif', size: 12 },
                    padding: 15,
                    usePointStyle: true,
                }
            }
        },
        scales: {
            y: {
                ticks: { color: CHART_COLORS.text },
                grid: { color: CHART_COLORS.border },
                beginAtZero: true,
            },
            x: {
                ticks: { color: CHART_COLORS.text },
                grid: { color: CHART_COLORS.border },
            }
        }
    };

    return new Chart(ctx, {
        type,
        data,
        options: { ...defaultOptions, ...options }
    });
}
