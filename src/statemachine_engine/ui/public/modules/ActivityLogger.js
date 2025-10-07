/**
 * ActivityLogger - Handles activity log display
 */
export class ActivityLogger {
    constructor(container) {
        this.container = container;
    }

    log(level, message) {
        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message">${message}</span>
        `;

        // Add to top of log
        this.container.insertBefore(entry, this.container.firstChild);

        // Keep only last 100 entries
        while (this.container.children.length > 100) {
            this.container.removeChild(this.container.lastChild);
        }
    }

    logJobStarted(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const jobId = payload.job_id || 'unknown';
        
        this.log('info', `${machineName}: Job ${jobId} started`);
    }

    logJobCompleted(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const jobId = payload.job_id || 'unknown';
        
        this.log('success', `${machineName}: Job ${jobId} completed`);
    }

    logError(data) {
        const machineName = data.machine_name;
        const payload = data.payload || {};
        const errorMessage = payload.error_message || 'Unknown error';
        const jobId = payload.job_id;
        
        const message = jobId ? 
            `${machineName}: Error in job ${jobId}: ${errorMessage}` :
            `${machineName}: ${errorMessage}`;
        
        this.log('error', message);
    }
}
