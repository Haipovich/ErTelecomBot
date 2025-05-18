-- 1. Пользователи (User)
-- Добавим еще одного пользователя, помимо того, что создает main.py
INSERT INTO public.users
(id, full_name, email, phone, gender, birth_date, city, education, work_experience, skills, desired_salary, desired_employment, relocation_readiness, about_me, photo, created_at, updated_at)
VALUES
(111222333, 'Елена Примерова', 'elena.p@example.com', '+79111112233', 'female', '1998-10-25', 'Москва', 'Высшее техническое', '1 год Python бэкенд', 'Python, Django, PostgreSQL, Docker', 100000.00, 'Полная занятость', true, 'Ищу интересные проекты для развития.', null, NOW(), NOW())
ON CONFLICT (id) DO NOTHING; -- Не добавлять, если пользователь с таким ID уже есть

-- 2. Вакансии/Стажировки (Jobs)
INSERT INTO public.jobs
(title, description, type, required_education, required_experience, required_skills, additional_skills, employment_type, work_schedule, workday_start, workday_end, salary, additional_info, is_active, created_at, updated_at)
VALUES
('Стажер Python-разработчик', 'Приглашаем активных студентов и выпускников на стажировку в отдел разработки. Обучение, менторство, реальные задачи.', 'internship', 'Неоконченное высшее / Высшее (техническое)', 'Без опыта / Минимальный опыт (учебные проекты)', 'Основы Python, понимание ООП, базовый SQL, Git', 'Знание Flask/Django будет плюсом', 'Стажировка', 'Гибкий (от 20 часов/нед)', '10:00:00', '19:00:00', 45000.00, 'Возможность трудоустройства по результатам стажировки.', true, NOW(), NOW()),
('Frontend-разработчик (Vue.js)', 'Ищем Middle Frontend разработчика в команду продукта. Разработка пользовательских интерфейсов, участие в проектировании.', 'vacancy', 'Высшее (желательно техническое)', 'От 2 лет коммерческой разработки', 'Vue.js (Vue 2/3), Vuex/Pinia, JavaScript (ES6+), HTML5, CSS3 (SASS/LESS)', 'TypeScript, Webpack/Vite, Jest/Vitest, опыт с UI-библиотеками', 'Полная занятость', 'Полный день (5/2)', '09:00:00', '18:00:00', 180000.00, 'ДМС, гибридный формат работы.', true, NOW(), NOW()),
('Java Backend Developer (архив)', 'Разработка высоконагруженных сервисов.', 'vacancy', 'Высшее техническое', 'От 3 лет', 'Java 11+, Spring Framework (Boot, MVC, Data), SQL, Kafka', 'Kubernetes, Docker, PostgreSQL', 'Полная занятость', 'Полный день', null, null, 250000.00, 'Эта вакансия уже закрыта.', false, NOW() - interval '1 month', NOW() - interval '1 month'); -- Неактивная вакансия

-- 3. Активности (Activities)
INSERT INTO public.activities
(title, description, start_time, end_time, address, target_audience, is_active, created_at, updated_at)
VALUES
('Онлайн Митап: Новинки Python 3.13', 'Обсуждаем новые фичи Python, делимся опытом. Спикеры из ведущих компаний.', NOW() + interval '7 day', NOW() + interval '7 day' + interval '2 hour', 'Онлайн (Ссылка будет отправлена зарегистрированным)', 'Разработчики Python (все уровни)', true, NOW(), NOW()),
('Летняя Школа Программирования', 'Интенсивный курс для студентов по основам веб-разработки.', NOW() + interval '1 month', NOW() + interval '2 month', 'Учебный центр "Прогресс", ауд. 501', 'Студенты 2-4 курсов', true, NOW(), NOW()),
('Хакатон "Город Будущего" (прошел)', 'Соревнование по разработке прототипов для умного города.', NOW() - interval '2 month', NOW() - interval '2 month' + interval '48 hour', 'Технопарк "Сколково"', 'Разработчики, дизайнеры, аналитики', true, NOW() - interval '3 month', NOW() - interval '2 month'); -- Активность в прошлом

-- 4. Частые вопросы (FAQ)
INSERT INTO public.faq
(question, answer, display_order)
VALUES
('Как подать заявку на стажировку?', 'Найдите интересующую вас стажировку в разделе "Вакансии и стажировки" и нажмите кнопку "Откликнуться". Убедитесь, что ваш профиль в боте заполнен актуальной информацией.', 10),
('Какие этапы отбора на вакансию?', 'Обычно этапы включают: рассмотрение резюме (анкеты в боте), техническое собеседование, финальное собеседование с руководителем. Для некоторых позиций может быть тестовое задание.', 20),
('Можно ли откликнуться на несколько вакансий?', 'Да, вы можете откликаться на несколько позиций, которые соответствуют вашему опыту и интересам.', 30),
('Как узнать статус моей заявки?', 'Статус вашей заявки отображается в разделе "Мои заявки". Мы стараемся обновлять статусы как можно быстрее.', 40);

-- 5. Контакты HR (hr_contacts)
INSERT INTO public.hr_contacts
(full_name, email, phone)
VALUES
('Мария Иванова', 'hr@example-company.com', '+74951234567') -- Используйте реальные данные для вашей компании
ON CONFLICT (email) DO NOTHING; -- Не добавлять, если email уже есть

-- 6. Контакты Компании (company_contacts)
INSERT INTO public.company_contacts
(department, email, phone)
VALUES
('Отдел подбора персонала', 'recruitment@example-company.com', '+74957654321'), -- Используйте реальные данные
('Общие вопросы', 'info@example-company.com', '+74950000000');

-- 7. Заявки (applications) - ОПЦИОНАЛЬНО
-- Добавим заявку от пользователя Елены (ID 111222333) на стажировку (предполагаем, что ее ID=1)
-- Важно: Убедитесь, что user_id и job_id/activity_id существуют!
INSERT INTO public.applications
(user_id, job_id, activity_id, status, hr_comment, application_time, created_at, updated_at)
VALUES
(111222333, 1, null, 'pending', null, NOW() - interval '1 day', NOW() - interval '1 day', NOW() - interval '1 day'); -- Заявка от Елены на Job ID=1

-- Можете добавить больше заявок для тестирования разных статусов

SELECT 'Тестовые данные добавлены!' as status;