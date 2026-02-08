#include <stdio.h>
#include <pthread.h>
#include <semaphore.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdarg.h>
#include <string.h>

#define MAX_JOBS 10
#define NEWSPAPER 1
#define MAGAZINE  2
#define AD_BANNER 3

typedef struct {
    int job_id;
    int pages;
    int category;
    int priority;
} PrintJob;

PrintJob jobQueue[MAX_JOBS];
int jobSubCount = 0;
PrintJob readyQueue[MAX_JOBS + 1];
int readyCount = 0;

pthread_mutex_t print_mutex;
pthread_mutex_t queue_mutex;
sem_t printer;

pthread_mutex_t submission_mutex;
pthread_cond_t submission_cv;
int submitted = 0;
volatile int shutdown_flag = 0;int i,j;

void safe_print(const char *format, ...) {
    va_list args;
    pthread_mutex_lock(&print_mutex);
    va_start(args, format);
    vprintf(format, args);
    fflush(stdout);
    va_end(args);
    pthread_mutex_unlock(&print_mutex);
}

const char* getTypeString(int category, int job_id) {
    if (job_id == -1)
        return "TERMINATE";
    static char buf[16];
    snprintf(buf, sizeof(buf), "%d", category);
    return buf;
}

void printJob(PrintJob job, char *dest, size_t destSize) {
    snprintf(dest, destSize, "(ID:%d, Pages:%d, Priority:%d, Type:%s)",
             job.job_id, job.pages, job.priority, getTypeString(job.category, job.job_id));
}

void displayQueues() {
    pthread_mutex_lock(&queue_mutex);
    safe_print("\n==================================================\n");
    safe_print("📋 Job Queue: [");
    char buf[128];int i=0;
    for ( i = 0; i < MAX_JOBS; i++) {
        if(i < jobSubCount) {
            printJob(jobQueue[i], buf, sizeof(buf));
            safe_print("%s", buf);
        } else {
            safe_print("None");
        }
        if (i < MAX_JOBS - 1)
            safe_print(", ");
    }
    safe_print("]\n");
    safe_print("🚀 Ready Queue: [");i=0;
    for (i = 0; i < readyCount; i++) {
        printJob(readyQueue[i], buf, sizeof(buf));
        safe_print("%s", buf);
        if (i < readyCount - 1)
            safe_print(", ");
    }
    safe_print("]\n");
    safe_print("==================================================\n");
    pthread_mutex_unlock(&queue_mutex);
}

void printSemaphoreStates() {
    int val;
    sem_getvalue(&printer, &val);
    safe_print("\n🔹 Semaphore States: printer = %d\n", val);
}

void sort_ready_queue() {
    int limit = readyCount;
    if (readyCount > 0 && readyQueue[readyCount - 1].job_id == -1) {
        limit = readyCount - 1;
    }i=0;j=0;
    for (i = 0; i < limit - 1; i++) {
        for ( j = 0; j < limit - i - 1; j++) {
            if (readyQueue[j].priority > readyQueue[j + 1].priority ||
               (readyQueue[j].priority == readyQueue[j + 1].priority &&
                readyQueue[j].pages > readyQueue[j + 1].pages)) {
                PrintJob temp = readyQueue[j];
                readyQueue[j] = readyQueue[j+1];
                readyQueue[j+1] = temp;
            }
        }
    }
}

void* job_submission(void* arg) {
    int num_jobs;
    if (scanf("%d", &num_jobs) != 1) {
        safe_print("Invalid input for number of jobs.\n");
        return NULL;
    }i=0;
    for (i = 0; i < num_jobs; i++) {
        PrintJob newJob;
        if (scanf("%d", &newJob.job_id) != 1 ||
            scanf("%d", &newJob.pages) != 1 ||
            scanf("%d", &newJob.category) != 1 ||
            scanf("%d", &newJob.priority) != 1) {
            safe_print("Invalid job input.\n");
            return NULL;
        }
        pthread_mutex_lock(&queue_mutex);
        if (jobSubCount < MAX_JOBS) {
            jobQueue[jobSubCount] = newJob;
            jobSubCount++;
            readyQueue[readyCount] = newJob;
            readyCount++;
        } else {
            safe_print("Job Queue is full! Cannot add Job ID: %d\n", newJob.job_id);
        }
        pthread_mutex_unlock(&queue_mutex);
        char jobInfo[128];
        printJob(newJob, jobInfo, sizeof(jobInfo));
        safe_print("\nJob Submitted: %s\n", jobInfo);
        displayQueues();
        sem_post(&printer);
    }
    pthread_mutex_lock(&queue_mutex);
    PrintJob term;
    term.job_id = -1;
    term.pages = -1;
    term.priority = -1;
    term.category = -1;
    readyQueue[readyCount] = term;
    readyCount++;
    pthread_mutex_unlock(&queue_mutex);
    safe_print("\n[Main] Submitting %d jobs for processing...\n", num_jobs);
    safe_print("[Main] All jobs submitted; processing will now begin.\n");
    pthread_mutex_lock(&submission_mutex);
    submitted = 1;
    pthread_cond_signal(&submission_cv);
    pthread_mutex_unlock(&submission_mutex);
    return NULL;
}

void* printer_function(void* arg) {
    pthread_mutex_lock(&submission_mutex);
    while (!submitted) {
        pthread_cond_wait(&submission_cv, &submission_mutex);
    }
    pthread_mutex_unlock(&submission_mutex);
    while (1) {
        sem_wait(&printer);
        pthread_mutex_lock(&queue_mutex);
        sort_ready_queue();
        if (readyCount == 1 && readyQueue[0].job_id == -1) {
            pthread_mutex_unlock(&queue_mutex);
            break;
        }
        PrintJob jobToPrint = readyQueue[0];i=0;
        for (i = 0; i < readyCount - 1; i++) {
            readyQueue[i] = readyQueue[i + 1];
        }
        readyCount--;
        pthread_mutex_unlock(&queue_mutex);
        safe_print("\n🖨️  Printing Job ID: %d, Pages: %d, Type: %s, Priority: %d...\n",
                   jobToPrint.job_id, jobToPrint.pages,
                   getTypeString(jobToPrint.category, jobToPrint.job_id),
                   jobToPrint.priority);
        int sleepTime = jobToPrint.pages / 2;
        if (sleepTime < 1)
            sleepTime = 1;
        sleep(sleepTime);
        safe_print("✅ Job ID: %d Printed Successfully!\n", jobToPrint.job_id);
        displayQueues();
        printSemaphoreStates();
    }
    return NULL;
}

int main() {
    pthread_t submission_thread, printer_thread;
    pthread_mutex_init(&print_mutex, NULL);
    pthread_mutex_init(&queue_mutex, NULL);
    pthread_mutex_init(&submission_mutex, NULL);
    pthread_cond_init(&submission_cv, NULL);
    sem_init(&printer, 0, 0);
    pthread_create(&printer_thread, NULL, printer_function, NULL);
    pthread_create(&submission_thread, NULL, job_submission, NULL);
    pthread_join(submission_thread, NULL);
    pthread_join(printer_thread, NULL);
    sem_destroy(&printer);
    pthread_mutex_destroy(&print_mutex);
    pthread_mutex_destroy(&queue_mutex);
    pthread_mutex_destroy(&submission_mutex);
    pthread_cond_destroy(&submission_cv);
    return 0;
}
