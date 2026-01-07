'use client';

import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { EventInput } from '@fullcalendar/core';

// Dummy events for January 2026
const dummyEvents: EventInput[] = [
  {
    id: '1',
    title: 'YouTube Video: React Tutorial',
    start: '2026-01-05',
    end: '2026-01-05',
    backgroundColor: '#3b82f6',
    borderColor: '#2563eb',
  },
  {
    id: '2',
    title: 'Instagram Post: Tech Tips',
    start: '2026-01-08T10:00:00',
    end: '2026-01-08T11:00:00',
    backgroundColor: '#ec4899',
    borderColor: '#db2777',
  },
  {
    id: '3',
    title: 'Blog Post: AI Trends',
    start: '2026-01-10',
    end: '2026-01-12',
    backgroundColor: '#10b981',
    borderColor: '#059669',
  },
  {
    id: '4',
    title: 'TikTok Video: Quick Tips',
    start: '2026-01-15T14:00:00',
    end: '2026-01-15T15:30:00',
    backgroundColor: '#8b5cf6',
    borderColor: '#7c3aed',
  },
  {
    id: '5',
    title: 'Podcast Recording',
    start: '2026-01-18T09:00:00',
    end: '2026-01-18T11:00:00',
    backgroundColor: '#f59e0b',
    borderColor: '#d97706',
  },
  {
    id: '6',
    title: 'LinkedIn Article: Career Growth',
    start: '2026-01-20',
    end: '2026-01-20',
    backgroundColor: '#0ea5e9',
    borderColor: '#0284c7',
  },
  {
    id: '7',
    title: 'Twitter Thread: Industry News',
    start: '2026-01-22T16:00:00',
    end: '2026-01-22T17:00:00',
    backgroundColor: '#06b6d4',
    borderColor: '#0891b2',
  },
  {
    id: '8',
    title: 'YouTube Live Stream',
    start: '2026-01-25T18:00:00',
    end: '2026-01-25T20:00:00',
    backgroundColor: '#ef4444',
    borderColor: '#dc2626',
  },
  {
    id: '9',
    title: 'Content Strategy Meeting',
    start: '2026-01-28T13:00:00',
    end: '2026-01-28T14:30:00',
    backgroundColor: '#6366f1',
    borderColor: '#4f46e5',
  },
  {
    id: '10',
    title: 'Newsletter Draft',
    start: '2026-01-30',
    end: '2026-01-31',
    backgroundColor: '#14b8a6',
    borderColor: '#0d9488',
  },
];

export default function CalendarPage() {
  const handleEventClick = (info: any) => {
    alert(`Event: ${info.event.title}\nStart: ${info.event.start}`);
  };

  const handleDateClick = (info: any) => {
    console.log('Date clicked:', info.dateStr);
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Content Creator Calendar</h1>
      <div className="bg-white rounded-lg shadow-lg p-6">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          initialDate="2026-01-01"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay',
          }}
          events={dummyEvents}
          eventClick={handleEventClick}
          dateClick={handleDateClick}
          editable={true}
          selectable={true}
          selectMirror={true}
          dayMaxEvents={true}
          weekends={true}
          height="auto"
        />
      </div>
    </div>
  );
}
