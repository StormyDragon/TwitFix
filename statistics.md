## Other stuff

Going to `https://fxtwitter.com/latest/` will present a page that shows the all the latest tweets that were added to the database, use with caution as results may be nsfw! Current page created by @DorukSaga

Using the `/dir/<video-url>` endpoint will return a redirect to the direct MP4 link, this can be useful for downloading a video

Using the `/dl/<video-url>` or appending a `.mp4` will make the server download the video and return a static, locally hosted copy

Using the subdomain `d.fxtwitter.com/<video-url>` will redirect to a direct MP4 url hosted on Twitter

Using the `/info/<video-url>` endpoint will return a json that contains all video info that youtube-dl can grab about any given video

Using `/other/<video-url>` will attempt to run the twitter embed stuff on other websites videos - This is mostly experimental and doesn't really work for now 

Using `/api/latest/` will return a json with the latest tweet added to the database. Takes params `?tweets=INT&=pageINT` to return multiple

Using `/api/top/` will return a json with the most hit tweet in the database. Takes params `?tweets=INT&=pageINT` to return multiple

Using `/api/stats/` will return a json with some stats about TwitFix's activity (embeds, new cached links, API hits, downloads). Takes param `?=date"YYYY-MM-DD"` to return a specific day, otherwise will return today's stats to far

Advanced embeds are provided via a `/oembed.json?` endpoint - This is manually pointing at the server in `/templates/index.html` and should be changed from `https://ayytwitter.com/` to whatever your domain is

We check for t.co links in non video tweets, and if one is found, we direct the discord useragent to embed that link directly, this means that twitter links containing youtube / vimeo links will automatically embed those as if you had just directly linked to that content
