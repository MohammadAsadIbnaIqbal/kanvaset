import React from "react";
import { Activity as ActivityIcon } from "lucide-react";
import type { Activity } from "../../types/project";

interface ActivitySidebarProps {
  activities: Activity[];
}

export const ActivitySidebar: React.FC<ActivitySidebarProps> = ({ activities }) => {
  return (
    <div className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col h-full">
      <div className="p-4 border-b border-slate-800/80 flex items-center space-x-2">
        <ActivityIcon className="w-4 h-4 text-slate-400" />
        <h3 className="text-sm font-semibold text-white">Project Activity</h3>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {activities.length === 0 ? (
          <div className="text-xs text-slate-500 text-center py-8">
            No activities yet.
          </div>
        ) : (
          activities.map((activity) => (
            <div key={activity.id} className="relative pl-4">
              <div className="absolute left-0 top-1.5 w-2 h-2 rounded-full bg-indigo-500/50 border border-indigo-500"></div>
              <div className="text-sm text-slate-300">
                <span className="font-semibold text-white">
                  {activity.user_id ? "User" : "System"}
                </span>{" "}
                <span className="text-slate-400">{activity.action_type}</span>{" "}
                {activity.metadata && activity.metadata.task_title && (
                  <span className="font-medium text-slate-300">
                    "{activity.metadata.task_title}"
                  </span>
                )}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {new Date(activity.created_at).toLocaleString()}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
