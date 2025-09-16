DROP TABLE articles;
DROP TABLE projects;

TRUNCATE TABLE public.projects; 
TRUNCATE TABLE public.articles; 

SELECT * FROM public.projects;
SELECT * FROM public.articles;

DROP TYPE articlestatus CASCADE;