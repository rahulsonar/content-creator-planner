export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 p-8">
      <main className="max-w-4xl mx-auto text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 dark:text-white mb-6">
          Content Creator Planner
        </h1>
        
        <p className="text-xl md:text-2xl text-gray-700 dark:text-gray-300 mb-8">
          Plan, organize, and schedule your content creation journey
        </p>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 mb-8">
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-4">
            Welcome to your all-in-one platform for content planning. Whether you're a YouTuber, 
            blogger, podcaster, or social media influencer, we help you stay organized and consistent.
          </p>
          
          <div className="grid md:grid-cols-3 gap-6 mt-8">
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                📅 Plan Ahead
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Create content calendars and never miss a posting schedule
              </p>
            </div>
            
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                💡 Organize Ideas
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Keep track of all your content ideas in one place
              </p>
            </div>
            
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                📊 Track Progress
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                Monitor your content performance and engagement
              </p>
            </div>
          </div>
        </div>
        
        <button className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-8 rounded-lg shadow-lg transition-colors duration-200">
          Get Started
        </button>
      </main>
    </div>
  );
}
