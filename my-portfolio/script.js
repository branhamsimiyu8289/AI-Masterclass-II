(function () {
  'use strict';

  var EMAIL = 'branhamsimiyu8289@gmail.com';
  var root = document.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function $(sel) { return document.querySelector(sel); }
  function $$(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  /* ---------- Footer year ---------- */
  var year = $('#year');
  if (year) year.textContent = new Date().getFullYear();

  /* ---------- Loader ---------- */
  var loader = $('#loader');
  function hideLoader() {
    if (!loader || loader.hidden) return;
    loader.classList.add('is-done');
    setTimeout(function () { loader.hidden = true; startReveal(); }, reduceMotion ? 0 : 480);
  }
  window.addEventListener('load', function () { setTimeout(hideLoader, reduceMotion ? 0 : 600); });
  setTimeout(hideLoader, 2800); // safety net if a CDN is slow

  /* ---------- Scroll progress ---------- */
  var progress = $('#progress');
  var ticking = false;
  function updateProgress() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = (max > 0 ? (window.scrollY / max) * 100 : 0) + '%';
    ticking = false;
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(updateProgress); }
  }, { passive: true });

  /* ---------- Theme ---------- */
  var themeBtn = $('#themeToggle');
  function currentTheme() { return root.getAttribute('data-theme') === 'light' ? 'light' : 'dark'; }
  function syncThemeButton() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    themeBtn.setAttribute('aria-label', 'Switch to ' + next + ' theme');
    themeBtn.setAttribute('title', 'Switch to ' + next + ' theme');
  }
  function toggleTheme() {
    var next = currentTheme() === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    try { localStorage.setItem('theme', next); } catch (e) {}
    syncThemeButton();
    return next;
  }
  themeBtn.addEventListener('click', toggleTheme);
  syncThemeButton();


  /* ---------- Hamburger menu ---------- */
  var menuBtn = $('#menuBtn');
  var menu = $('#siteMenu');
  function setMenu(open) {
    menu.hidden = !open;
    menuBtn.setAttribute('aria-expanded', String(open));
    menuBtn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
  menuBtn.addEventListener('click', function () { setMenu(menu.hidden); });
  menu.addEventListener('click', function (e) { if (e.target.closest('a')) setMenu(false); });
  document.addEventListener('click', function (e) {
    if (!menu.hidden && !menu.contains(e.target) && !menuBtn.contains(e.target)) setMenu(false);
  });

  /* ---------- Active menu item while scrolling ---------- */
  var tabs = $$('.menu a');
  if ('IntersectionObserver' in window) {
    var sectionObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        tabs.forEach(function (tab) {
          var on = tab.getAttribute('data-tab') === entry.target.id;
          tab.classList.toggle('is-active', on);
          if (on) tab.setAttribute('aria-current', 'true'); else tab.removeAttribute('aria-current');
        });
      });
    }, { rootMargin: '-40% 0px -55% 0px' });
    tabs.forEach(function (tab) {
      var section = document.getElementById(tab.getAttribute('data-tab'));
      if (section) sectionObserver.observe(section);
    });
  }

  /* ---------- Helpers ---------- */
  function go(id) {
    var el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
  }

  var toastEl = $('#toast');
  var toastTimer;
  function toast(message) {
    toastEl.textContent = message;
    toastEl.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove('show'); }, 2200);
  }

  function copyEmail() {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(EMAIL).then(
        function () { toast('Email address copied'); },
        function () { toast(EMAIL); }
      );
    } else {
      toast(EMAIL);
    }
  }
  $('#copyEmail').addEventListener('click', copyEmail);

  /* ---------- Contact form: opens the visitor's email app ---------- */
  var form = $('#contactForm');
  var formStatus = $('#formStatus');
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var name = form.elements.name.value.trim();
    var from = form.elements.email.value.trim();
    var message = form.elements.message.value.trim();
    var subject = 'Portfolio enquiry from ' + name;
    var body = message + '\n\n' + name + '\nReply to: ' + from;
    window.location.href = 'mailto:' + EMAIL + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
    formStatus.textContent = 'Opening your email app. If nothing opens, write to ' + EMAIL + '.';
  });

  /* ---------- Copy code snippet in about.py ---------- */
  var copyCodeBtn = $('#copyCodeBtn');
  if (copyCodeBtn) {
    copyCodeBtn.addEventListener('click', function () {
      var code = $('#about .code');
      var text = code ? (code.innerText || code.textContent) : '';
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text.trim()).then(
          function () { toast('Copied about.py snippet'); },
          function () { toast('Unable to copy code snippet'); }
        );
      } else {
        toast('Copied about.py snippet');
      }
    });
  }

  /* ---------- Scroll to top button ---------- */
  var scrollTopBtn = $('#scrollTopBtn');
  if (scrollTopBtn) {
    window.addEventListener('scroll', function () {
      scrollTopBtn.classList.toggle('is-visible', window.scrollY > 350);
    }, { passive: true });
    scrollTopBtn.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
    });
  }

  /* ---------- Project category filters ---------- */
  var filterBtns = $$('.filter-btn');
  var projectCards = $$('.project-list .project');
  function applyFilter(cat) {
    filterBtns.forEach(function (btn) {
      var match = btn.getAttribute('data-filter') === cat;
      btn.classList.toggle('is-active', match);
      btn.setAttribute('aria-selected', String(match));
    });
    projectCards.forEach(function (card) {
      var categories = (card.getAttribute('data-category') || '').split(/\s+/);
      var show = cat === 'all' || categories.indexOf(cat) !== -1;
      card.setAttribute('data-hidden', show ? 'false' : 'true');
    });
  }
  filterBtns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var cat = btn.getAttribute('data-filter');
      applyFilter(cat);
    });
  });


  /* ---------- Live Demo preview window ---------- */
  var demo = $('#demo');
  var demoFrame = $('#demoFrame');
  var demoOutput = $('#demoOutput');
  var demoTitle = $('#demoTitle');
  var demoOpen = $('#demoOpen');
  var demoNote = $('#demoNote');
  var demoClose = $('#demoClose');
  var demoFocus = null;

  function openDemo(btn) {
    var url = btn.getAttribute('data-demo') || '';
    var outId = btn.getAttribute('data-output') || '';
    var name = btn.getAttribute('data-name') || 'Project';
    var repo = btn.getAttribute('data-repo') || 'https://github.com/branhamsimiyu8289';
    demoFocus = document.activeElement;
    demoFrame.classList.remove('ready');
    if (url) {
      demoTitle.textContent = name + ' | live demo';
      demoOutput.hidden = true;
      demoFrame.hidden = false;
      demoFrame.title = name + ' live demo';
      demoOpen.querySelector('span').textContent = 'Open in new tab';
      demoOpen.href = url;
      demoOpen.hidden = false;
      demoNote.hidden = false;
      demoFrame.src = url;
    } else {
      var tpl = document.getElementById(outId);
      demoTitle.textContent = name + ' | example output';
      demoFrame.hidden = true;
      demoFrame.src = 'about:blank';
      demoOutput.textContent = tpl ? tpl.content.textContent : 'No preview available yet.';
      demoOutput.hidden = false;
      demoOutput.scrollTop = 0;
      demoOpen.querySelector('span').textContent = 'View on GitHub';
      demoOpen.href = repo;
      demoOpen.hidden = false;
      demoNote.hidden = true;
    }
    demo.hidden = false;
    document.body.classList.add('modal-open');
    demoClose.focus();
  }
  function closeDemo() {
    if (demo.hidden) return;
    demo.hidden = true;
    demoFrame.src = 'about:blank';
    document.body.classList.remove('modal-open');
    if (demoFocus && demoFocus.focus) demoFocus.focus();
  }
  demoFrame.addEventListener('load', function () {
    var src = demoFrame.getAttribute('src');
    if (src && src !== 'about:blank') demoFrame.classList.add('ready');
  });
  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.plink-see') : null;
    if (btn) openDemo(btn);
  });
  demoClose.addEventListener('click', closeDemo);
  demo.addEventListener('mousedown', function (e) { if (e.target === demo) closeDemo(); });
  demo.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    var items = Array.prototype.filter.call(demo.querySelectorAll('button, a[href]'), function (el) { return !el.hidden && el.offsetParent !== null; });
    if (!items.length) return;
    var first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  /* ---------- Command palette ---------- */
  var palette = $('#palette');
  var paletteInput = $('#paletteInput');
  var paletteList = $('#paletteList');
  var lastFocus = null;
  var activeIndex = 0;
  var visible = [];

  var commands = [
    { label: 'Go to About', run: function () { go('about'); } },
    { label: 'Go to Skills', run: function () { go('skills'); } },
    { label: 'Go to Projects', run: function () { go('projects'); } },
    { label: 'Go to Services', run: function () { go('services'); } },
    { label: 'Go to Experience', run: function () { go('experience'); } },
    { label: 'Go to Reviews / Testimonials', run: function () { go('testimonials'); } },
    { label: 'Go to Contact', run: function () { go('contact'); } },
    { label: 'Filter: All Projects', run: function () { applyFilter('all'); go('projects'); } },
    { label: 'Filter: Python & APIs', run: function () { applyFilter('python'); go('projects'); } },
    { label: 'Filter: Web & PWAs', run: function () { applyFilter('web'); go('projects'); } },
    { label: 'Filter: Data & ML', run: function () { applyFilter('data'); go('projects'); } },
    { label: 'Project: Kichuma Structures', run: function () { go('proj-kichuma'); } },
    { label: 'Project: Amerix Health App', run: function () { go('proj-amerix'); } },
    { label: 'Project: SMP Tracker', run: function () { go('proj-smp'); } },
    { label: 'Project: SMP Command Centre', run: function () { go('proj-dashboard'); } },
    { label: 'Project: 28-Day Fitness Analysis', run: function () { go('proj-analysis'); } },
    { label: 'Project: Weather App', run: function () { go('proj-weather'); } },
    { label: 'Project: Titans Cabinet', run: function () { go('proj-titans'); } },
    { label: 'Download resume', run: function () { $('#resumeBtn').click(); } },
    { label: 'Copy email address', run: copyEmail },
    { label: 'Open WhatsApp', run: function () { window.open('https://wa.me/254786753636', '_blank', 'noopener'); } },
    { label: 'Open GitHub', run: function () { window.open('https://github.com/branhamsimiyu8289', '_blank', 'noopener'); } },
    { label: 'Open LinkedIn', run: function () { window.open('https://www.linkedin.com/in/branham-simiyu', '_blank', 'noopener'); } },
    { label: 'Switch theme', run: function () { toggleTheme(); } },
    { label: 'Focus terminal', run: function () { selectPane('paneTerminal'); go('terminalInput'); setTimeout(function () { terminalInput.focus(); }, 300); } }
  ];

  function renderPalette(filter) {
    var q = (filter || '').toLowerCase().trim();
    visible = commands.filter(function (c) { return c.label.toLowerCase().indexOf(q) !== -1; });
    activeIndex = 0;
    paletteList.innerHTML = '';
    if (!visible.length) {
      var empty = document.createElement('li');
      empty.className = 'palette-empty';
      empty.textContent = 'No matching command';
      paletteList.appendChild(empty);
      return;
    }
    visible.forEach(function (cmd, i) {
      var li = document.createElement('li');
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', i === 0 ? 'true' : 'false');
      li.textContent = cmd.label;
      li.addEventListener('click', function () { runPalette(i); });
      li.addEventListener('mousemove', function () { setActive(i); });
      paletteList.appendChild(li);
    });
  }

  function setActive(i) {
    var items = paletteList.querySelectorAll('li[role="option"]');
    if (!items.length) return;
    activeIndex = (i + items.length) % items.length;
    Array.prototype.forEach.call(items, function (li, idx) {
      li.setAttribute('aria-selected', idx === activeIndex ? 'true' : 'false');
    });
    items[activeIndex].scrollIntoView({ block: 'nearest' });
  }

  function openPalette() {
    lastFocus = document.activeElement;
    palette.hidden = false;
    paletteInput.value = '';
    renderPalette('');
    paletteInput.focus();
  }
  function closePalette() {
    palette.hidden = true;
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function runPalette(i) {
    var cmd = visible[i];
    if (!cmd) return;
    palette.hidden = true;
    lastFocus = null;
    cmd.run();
  }

  paletteInput.addEventListener('input', function () { renderPalette(paletteInput.value); });
  paletteInput.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(activeIndex + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(activeIndex - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); runPalette(activeIndex); }
    else if (e.key === 'Tab') { e.preventDefault(); } // keep focus inside the dialog
  });
  palette.addEventListener('mousedown', function (e) { if (e.target === palette) closePalette(); });

  document.addEventListener('keydown', function (e) {
    var mod = e.ctrlKey || e.metaKey;
    var key = (e.key || '').toLowerCase();
    if (mod && (key === 'k' || (e.shiftKey && key === 'p'))) {
      e.preventDefault();
      if (palette.hidden) openPalette(); else closePalette();
    } else if (key === 'escape' && !palette.hidden) {
      closePalette();
    } else if (key === 'escape' && !demo.hidden) {
      closeDemo();
    } else if (key === 'escape' && !menu.hidden) {
      setMenu(false);
      menuBtn.focus();
    }
  });
  $('#paletteBtn').addEventListener('click', openPalette);
  $('#termPalette').addEventListener('click', openPalette);

  /* ---------- Terminal ---------- */
  var terminalInput = $('#terminalInput');
  var terminalOutput = $('#terminalOutput');
  var history = [];
  var historyPos = 0;
  var sections = ['about', 'skills', 'projects', 'services', 'experience', 'testimonials', 'contact'];

  function print(text, cls) {
    var p = document.createElement('p');
    p.className = cls || 't-out';
    p.textContent = text;
    terminalOutput.appendChild(p);
  }

  var responses = {
    help: [
      'Available commands:',
      '  whoami            who I am',
      '  about             a short bio',
      '  skills            my tech stack',
      '  projects          what I have built',
      '  services          how I can help',
      '  experience        timeline & career journey',
      '  testimonials      client reviews and feedback',
      '  stats             portfolio metrics & numbers',
      '  filter <category> filter projects (all|python|web|data)',
      '  contact           ways to reach me',
      '  resume            download my resume (PDF)',
      '  github            open my GitHub profile',
      '  email             copy my email address',
      '  ls                list the sections and files',
      '  open <section>    jump to a section',
      '  theme             switch light and dark',
      '  clear             clear the terminal'
    ],
    whoami: ['Branham Simiyu, Python and Web Developer'],
    about: [
      'Python and web developer building frontend and backend systems, automated workflows and data-driven applications.',
      'Core work: FastAPI REST APIs, automation scripts and machine learning for practical problems.',
      'Responsive websites, PWAs, full-stack tools and live dashboards. Learning UI and UX, React and Node.js, and MongoDB.'
    ],
    skills: [
      'Languages:       Python, JavaScript, HTML5, CSS3',
      'Libraries:       FastAPI, Pandas, NumPy, Scikit-Learn',
      'Specializations: workflow automation, machine learning, data analysis, web scraping, API engineering, website development',
      'Web:             React.js, responsive websites, PWAs',
      'Tools:           Matplotlib, Git, GitHub, RESTful APIs, interactive dashboards'
    ],
    projects: [
      '1. Kichuma Structures website',
      '2. Amerix Health App Advisor',
      '3. SMP Tracker',
      '4. SMP Command Centre Dashboard',
      '5. 28-Day Fitness Data Analysis',
      '6. Weather App',
      '7. Titans Cabinet (installable game)',
      'Run "open projects" for the details.'
    ],
    services: [
      '1. Responsive websites and PWAs',
      '2. Data pipeline and workflow automation',
      '3. Custom REST APIs and live dashboards',
      '4. Machine learning and predictive solutions'
    ],
    experience: [
      '2024 - Present: Full-Stack Python & Web Developer (Freelance)',
      '  * FastAPI REST APIs, Automation Scripts, Responsive Websites, PWAs',
      '2024: AI Masterclass & Systems Specialization',
      '  * Pandas, NumPy, Scikit-Learn data science & analytics pipelines',
      '2023 - 2024: Web Architecture & Frontend Engineering',
      '  * Modern JavaScript (ES6+), PWA caching, HTML5 & CSS3 layouts'
    ],
    testimonials: [
      '1. "Exceptional responsive platform for Kichuma Structures... increased client inquiries."',
      '2. "The automated Python reporting & FastAPI backend cut manual tracking to zero."',
      '3. "Impressive craft with PWAs and vanilla JS... runs silky smooth offline."'
    ],
    reviews: [
      '1. "Exceptional responsive platform for Kichuma Structures... increased client inquiries."',
      '2. "The automated Python reporting & FastAPI backend cut manual tracking to zero."',
      '3. "Impressive craft with PWAs and vanilla JS... runs silky smooth offline."'
    ],
    stats: [
      'Total Projects:   7 featured projects',
      'Tech Stack:       FastAPI, Python, JavaScript, HTML5, CSS3, SQL, ML',
      'Live Demos:       Available on Vercel & GitHub Pages',
      'Status:           Open to freelance & full-time opportunities'
    ],
    sudo: ['Permission denied: Guest user session. Nice try though! :)'],
    date: [new Date().toString()],
    contact: [
      'Email:    ' + EMAIL,
      'WhatsApp: +254 786 753 636',
      'Telegram: @branhamsimiyu76',
      'LinkedIn: linkedin.com/in/branham-simiyu',
      'GitHub:   github.com/branhamsimiyu8289'
    ],
    ls: ['about.py  skills.json  projects.py  services.md  experience.log  reviews.json  contact.json']
  };

  function runCommand(raw) {
    var line = document.createElement('p');
    line.className = 't-cmd';
    var user = document.createElement('span');
    user.className = 't-user';
    user.textContent = 'branham@portfolio';
    var path = document.createElement('span');
    path.className = 't-path';
    path.textContent = '~';
    line.appendChild(user);
    line.appendChild(document.createTextNode(':'));
    line.appendChild(path);
    line.appendChild(document.createTextNode('$ ' + raw));
    terminalOutput.appendChild(line);

    var parts = raw.trim().toLowerCase().split(/\s+/);
    var cmd = parts[0];
    var arg = parts[1];

    if (!cmd) {
      // empty line, nothing to print
    } else if (cmd === 'clear') {
      terminalOutput.innerHTML = '';
      return;
    } else if (cmd === 'open') {
      if (arg && sections.indexOf(arg) !== -1) { print('Opening ' + arg + '...'); go(arg); }
      else print('Usage: open <' + sections.join(' | ') + '>', 't-dim');
    } else if (cmd === 'filter') {
      if (arg && ['all', 'python', 'web', 'data'].indexOf(arg) !== -1) {
        applyFilter(arg);
        print('Filtered projects by: ' + arg, 't-ok');
        go('projects');
      } else {
        print('Usage: filter <all | python | web | data>', 't-dim');
      }
    } else if (cmd === 'resume') {
      print('Downloading Branham_Simiyu_CV.pdf...');
      $('#resumeBtn').click();
    } else if (cmd === 'github') {
      print('Opening github.com/branhamsimiyu8289...');
      window.open('https://github.com/branhamsimiyu8289', '_blank', 'noopener');
    } else if (cmd === 'email') {
      copyEmail();
      print('Copied ' + EMAIL);
    } else if (cmd === 'theme') {
      print('Switched to the ' + toggleTheme() + ' theme.');
    } else if (responses[cmd]) {
      responses[cmd].forEach(function (text) { print(text); });
    } else {
      print('Command not found: ' + cmd + '. Type help for the list.', 't-dim');
    }
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  terminalInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      var value = terminalInput.value;
      if (value.trim()) { history.push(value); }
      historyPos = history.length;
      runCommand(value);
      terminalInput.value = '';
    } else if (e.key === 'ArrowUp') {
      if (history.length) {
        e.preventDefault();
        historyPos = Math.max(0, historyPos - 1);
        terminalInput.value = history[historyPos] || '';
      }
    } else if (e.key === 'ArrowDown') {
      if (history.length) {
        e.preventDefault();
        historyPos = Math.min(history.length, historyPos + 1);
        terminalInput.value = history[historyPos] || '';
      }
    }
  });


  /* ---------- Terminal panel tabs and toolbar ---------- */
  var paneTabs = $$('.term-tabs [role="tab"]');
  var termEl = $('.term');
  function selectPane(id) {
    paneTabs.forEach(function (tab) {
      var on = tab.getAttribute('aria-controls') === id;
      tab.setAttribute('aria-selected', String(on));
      tab.tabIndex = on ? 0 : -1;
      document.getElementById(tab.getAttribute('aria-controls')).hidden = !on;
    });
  }
  paneTabs.forEach(function (tab, i) {
    tab.addEventListener('click', function () {
      selectPane(tab.getAttribute('aria-controls'));
    });
    tab.addEventListener('keydown', function (e) {
      var next = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : -1;
      if (next < 0) return;
      e.preventDefault();
      var target = paneTabs[(next + paneTabs.length) % paneTabs.length];
      selectPane(target.getAttribute('aria-controls'));
      target.focus();
    });
  });

  function intro() {
    print('Branham Simiyu portfolio, version 1.0', 't-ok');
    var p = document.createElement('p');
    p.className = 't-dim';
    var hl = document.createElement('span');
    hl.className = 't-hl';
    hl.textContent = 'help';
    p.appendChild(document.createTextNode('Type '));
    p.appendChild(hl);
    p.appendChild(document.createTextNode(' to see available commands.'));
    terminalOutput.appendChild(p);
  }
  $('#termNew').addEventListener('click', function () {
    terminalOutput.innerHTML = '';
    intro();
    selectPane('paneTerminal');
    terminalInput.focus();
  });
  $('#termClear').addEventListener('click', function () {
    terminalOutput.innerHTML = '';
    selectPane('paneTerminal');
    terminalInput.focus();
  });
  $('#termMax').addEventListener('click', function () {
    var on = termEl.classList.toggle('max');
    this.setAttribute('aria-pressed', String(on));
    this.title = on ? 'Restore Panel Size' : 'Maximize Panel Size';
    this.setAttribute('aria-label', on ? 'Restore panel size' : 'Maximize panel size');
  });
  // clicking the output focuses the prompt on mouse devices, like the real terminal
  terminalOutput.addEventListener('mouseup', function () {
    if (window.matchMedia && window.matchMedia('(pointer: fine)').matches && !String(window.getSelection())) terminalInput.focus();
  });

  /* ---------- Entrance animations ---------- */
  var targets = [];
  var revealStarted = false;
  var revealedCount = 0;
  var plan = [
    ['.hero h1', 'up'], ['.hero .lede', 'up'], ['.hero .actions', 'up'], ['.hero .orbit-wrap', 'zoom'],
    ['#skills h2', 'down'],
    ['main section:not(.hero):not(.term) .comment', 'left'],
    ['main section:not(.hero):not(.term) h2', 'up'],
    ['.section-intro', 'blur'],
    ['#about .win', 'left'], ['.stack-cards .card', 'right'],
    ['#skills .win', 'left'], ['.skill', 'zoom'],
    ['.project-list .project:nth-child(odd)', 'left'], ['.project-list .project:nth-child(even)', 'right'],
    ['.project-filters', 'up'],
    ['.service', 'flip'],
    ['.timeline-item', 'up'],
    ['.review-card', 'flip'],
    ['#contact .win', 'left'], ['.reach h3', 'up'], ['.reach > p', 'up'], ['.email-row', 'right'], ['.contact-icons li:nth-child(odd)', 'flipr'], ['.contact-icons li:nth-child(even)', 'flipl'],
    ['.term', 'up']
  ];

  function prepLive() {
    var code = $('#about .code');
    if (code) {
      code.innerHTML = code.innerHTML.split('\n').map(function (line, i) {
        return '<span class="ln" style="--i:' + i + '">' + (line || '&#8203;') + '</span>';
      }).join('');
    }
    $$('.tree li').forEach(function (li, i) { li.style.setProperty('--i', i); });
    $$('.tool-chips').forEach(function (group) {
      Array.prototype.forEach.call(group.children, function (chip, i) { chip.style.setProperty('--i', i); });
    });
  }

  function tagTargets() {
    plan.forEach(function (p) {
      $$(p[0]).forEach(function (el) {
        if (el.hasAttribute('data-anim')) return;
        el.setAttribute('data-anim', p[1]);
        targets.push(el);
      });
    });
    var typing = $('.hero .comment');
    if (typing) targets.push(typing);
  }

  function reveal(el, delay) {
    revealedCount++;
    if (el.hasAttribute('data-anim')) {
      el.style.setProperty('--d', delay + 'ms');
      el.classList.add('in');
    }
    var code = el.querySelector('.code'); if (code) code.classList.add('typed');
    var tree = el.querySelector('.tree'); if (tree) tree.classList.add('typed');
    if (el.classList.contains('project')) el.classList.add('live');
    if (el.classList.contains('comment')) el.classList.add('go');
  }

  function hide(el) {
    el.classList.remove('in', 'live', 'go');
    var code = el.querySelector('.code'); if (code) code.classList.remove('typed');
    var tree = el.querySelector('.tree'); if (tree) tree.classList.remove('typed');
  }

  function startReveal() {
    if (revealStarted) return;
    revealStarted = true;
    if (!targets.length) return;
    var shown = new Set();
    var io = new IntersectionObserver(function (entries) {
      var entering = 0;
      entries.forEach(function (entry) {
        var el = entry.target;
        if (entry.intersectionRatio >= 0.12 && !shown.has(el)) {
          shown.add(el);
          reveal(el, Math.min(entering * 90, 450)); // stagger items that arrive together
          entering++;
        }
      });
    }, { threshold: [0, 0.12], rootMargin: '0px 0px -6% 0px' });
    // reset a block only once it is well off screen, so nothing blinks out while you scroll
    var far = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting && shown.has(entry.target)) {
          shown.delete(entry.target);
          hide(entry.target);
        }
      });
    }, { rootMargin: '120% 0px 120% 0px' });
    targets.forEach(function (el) { io.observe(el); far.observe(el); });
    // safety net: if nothing ever revealed, show the page as-is
    setTimeout(function () { if (!revealedCount) root.classList.remove('anim'); }, 8000);
  }

  if (!reduceMotion && 'IntersectionObserver' in window) {
    root.classList.add('anim');
    prepLive();
    tagTargets();
  }
  if (!loader) startReveal();
})();
