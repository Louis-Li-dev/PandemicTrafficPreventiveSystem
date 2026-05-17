document.addEventListener('DOMContentLoaded', () => {
    let currentPredictionData = null;
    const buildBtn = document.getElementById('buildBtn');
    const traceBtn = document.getElementById('traceBtn');
    const traceSection = document.getElementById('traceSection');
    
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const loader = document.getElementById('loader');
    const loaderText = document.getElementById('loaderText');
    
    const emptyState = document.getElementById('emptyState');
    const hubsView = document.getElementById('hubsView');
    const impactView = document.getElementById('impactView');
    const warningView = document.getElementById('warningView');
    const trafficView = document.getElementById('trafficView');
    
    const hubsPlot = document.getElementById('hubsPlot');
    const impactPlotPaths = document.getElementById('impactPlotPaths');
    const impactPlotHubs = document.getElementById('impactPlotHubs');
    // Elements
    const datasetSelect = document.getElementById('datasetSelect');
    const numUsersInput = document.getElementById('numUsers');
    const radiusKInput = document.getElementById('radiusK');
    
    const tab1Btn = document.getElementById('tab1Btn');
    const tab2Btn = document.getElementById('tab2Btn');
    const tab3Btn = document.getElementById('tab3Btn');
    const tab4Btn = document.getElementById('tab4Btn');
    const downloadCsvBtn = document.getElementById('downloadCsvBtn');
    
    const primaryTableBody = document.querySelector('#primaryTable tbody');
    const secondaryTableBody = document.querySelector('#secondaryTable tbody');
    
    const targetDaySelect = document.getElementById('targetDay');
    const targetHubSelect = document.getElementById('targetHub');
    
    const timeStartInput = document.getElementById('timeStart');
    const timeEndInput = document.getElementById('timeEnd');
    const timeStartHint = document.getElementById('timeStartHint');
    const timeEndHint = document.getElementById('timeEndHint');
    
    function formatTimeHint(t) {
        const hours = Math.floor((t * 30) / 60);
        const mins = (t * 30) % 60;
        return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
    }
    
    timeStartInput.addEventListener('input', (e) => {
        timeStartHint.textContent = formatTimeHint(e.target.value);
    });
    
    timeEndInput.addEventListener('input', (e) => {
        timeEndHint.textContent = formatTimeHint(e.target.value);
    });
    
    function setStatus(status, text) {
        statusDot.className = `dot ${status}`;
        statusText.textContent = text;
    }
    
    function showLoader(text) {
        loaderText.textContent = text;
        loader.classList.remove('hidden');
    }
    
    function hideLoader() {
        loader.classList.add('hidden');
    }
    
    function switchTab(targetViewId) {
        [hubsView, impactView, warningView, trafficView].forEach(v => v.classList.add('hidden'));
        [tab1Btn, tab2Btn, tab3Btn, tab4Btn].forEach(b => b.classList.remove('active'));
        
        document.getElementById(targetViewId).classList.remove('hidden');
        if(targetViewId === 'hubsView') tab1Btn.classList.add('active');
        if(targetViewId === 'impactView') tab2Btn.classList.add('active');
        if(targetViewId === 'warningView') tab3Btn.classList.add('active');
        if(targetViewId === 'trafficView') tab4Btn.classList.add('active');
    }
    
    tab1Btn.addEventListener('click', () => switchTab('hubsView'));
    tab2Btn.addEventListener('click', () => switchTab('impactView'));
    tab3Btn.addEventListener('click', () => switchTab('warningView'));
    tab4Btn.addEventListener('click', () => switchTab('trafficView'));
    
    // Fetch datasets on load
    async function fetchDatasets() {
        try {
            const res = await fetch('/api/datasets');
            const data = await res.json();
            if (data.status === 'success') {
                datasetSelect.innerHTML = '';
                data.datasets.forEach(ds => {
                    const option = document.createElement('option');
                    option.value = ds;
                    option.textContent = ds;
                    datasetSelect.appendChild(option);
                });
                setStatus('online', '伺服器已連線 (請點擊「建立全域 Hubs」)');
            } else {
                setStatus('offline', '讀取資料集失敗');
            }
        } catch(err) {
            console.error('Failed to load datasets', err);
            setStatus('offline', '系統未連線 (伺服器未啟動)');
        }
    }
    
    // Initialize datasets
    fetchDatasets();
    
    // Build Hubs
    buildBtn.addEventListener('click', async () => {
        const numUsers = parseInt(numUsersInput.value);
        const radiusK = parseFloat(radiusKInput.value);
        const dataset = datasetSelect.value;
        
        buildBtn.disabled = true;
        buildBtn.textContent = '計算中...';
        
        try {
            const response = await fetch('/api/build_hubs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ numUsers, radiusK, dataset })
            });
            
            const data = await response.json();
            
            if(data.status === 'success') {
                // Show Plot
                hubsPlot.src = data.hubs_plot;
                document.getElementById('globalHubsCount').textContent = data.global_hubs_count;
                document.getElementById('localHubsCount').textContent = data.local_hubs_count;
                
                // Fetch Options
                const optsResponse = await fetch('/api/get_options');
                const optsData = await optsResponse.json();
                
                targetDaySelect.innerHTML = optsData.days.map(d => `<option value="${d}">第 ${d} 天</option>`).join('');
                targetHubSelect.innerHTML = optsData.hubs.map(h => `<option value="${h}">G${h}</option>`).join('');
                
                // Update UI
                emptyState.classList.add('hidden');
                switchTab('hubsView');
                
                traceSection.style.opacity = '1';
                traceSection.style.pointerEvents = 'auto';
                tab2Btn.disabled = false;
                tab3Btn.disabled = false;
                tab4Btn.disabled = false;
                
                const trafficDaySelect = document.getElementById('trafficDay');
                const trafficHubSelect = document.getElementById('trafficHub');
                const warningDaySelect = document.getElementById('warningDay');
                const warningHubSelect = document.getElementById('warningHub');
                
                const dayOptions = optsData.days.map(d => `<option value="${d}">第 ${d} 天</option>`).join('');
                const hubOptions = optsData.hubs.map(h => `<option value="${h}">G${h}</option>`).join('');
                
                if (trafficDaySelect) trafficDaySelect.innerHTML = dayOptions;
                if (trafficHubSelect) trafficHubSelect.innerHTML = hubOptions;
                if (warningDaySelect) warningDaySelect.innerHTML = dayOptions;
                if (warningHubSelect) warningHubSelect.innerHTML = hubOptions;
                
                setStatus('online', `系統就緒 (${data.global_hubs_count} 個 Global Hubs)`);
            }
        } catch (err) {
            console.error(err);
            setStatus('offline', '建立 Hubs 發生錯誤');
            alert('無法建立 Hubs，請查看控制台詳細資訊。');
        } finally {
            buildBtn.disabled = false;
            buildBtn.textContent = '建立全域 Hubs';
            hideLoader();
        }
    });
    
    traceBtn.addEventListener('click', async () => {
        const day = parseInt(targetDaySelect.value);
        const hub = parseInt(targetHubSelect.value);
        const tStart = parseInt(timeStartInput.value);
        const tEnd = parseInt(timeEndInput.value);
        
        if(tStart > tEnd) {
            alert('時間區間起點必須小於或等於終點。');
            return;
        }
        
        showLoader('追蹤連鎖影響中...');
        setStatus('processing', '分析中...');
        
        try {
            const response = await fetch('/api/trace_cascade', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ day, hub, tStart, tEnd })
            });
            
            const data = await response.json();
            
            if(data.status === 'success') {
                currentPredictionData = data;
                downloadCsvBtn.style.display = 'block';
                
                impactPlotPaths.src = data.impact_plot_paths;
                impactPlotHubs.src = data.impact_plot_hubs;
                
                const populateTable = (tbody, users) => {
                    tbody.innerHTML = '';
                    if(users.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">無受影響使用者</td></tr>';
                    } else {
                        users.forEach(u => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${u.uid}</td>
                                <td>G${u.hub}</td>
                                <td>${u.time}</td>
                            `;
                            tbody.appendChild(tr);
                        });
                    }
                };
                
                populateTable(primaryTableBody, data.primary_users);
                populateTable(secondaryTableBody, data.secondary_users);
                
                switchTab('impactView');
                
                setStatus('online', `追蹤完成 (${data.primary_users.length} 位 Primary, ${data.secondary_users.length} 位 Secondary)`);
            }
        } catch (err) {
            console.error(err);
            setStatus('online', '追蹤發生錯誤');
            alert('追蹤連鎖影響失敗，請查看控制台詳細資訊。');
        } finally {
            hideLoader();
        }
    });
    
    downloadCsvBtn.addEventListener('click', () => {
        if (!currentPredictionData) return;
        
        let csvContent = "層級,UID,被影響 Hub ID,預計影響時間\n";
        
        currentPredictionData.primary_users.forEach(u => {
            csvContent += `第一層,${u.uid},G${u.hub},${u.time}\n`;
        });
        
        currentPredictionData.secondary_users.forEach(u => {
            csvContent += `第二層,${u.uid},G${u.hub},${u.time}\n`;
        });
        
        const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
        const blob = new Blob([bom, csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `cascade_prediction_day${targetDaySelect.value}_hub${targetHubSelect.value}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });
    
    // ==========================================
    // Warning System Logic
    // ==========================================
    const trajectoryBody = document.getElementById('trajectoryBody');
    const addTrajBtn = document.getElementById('addTrajBtn');
    const checkWarningBtn = document.getElementById('checkWarningBtn');
    const warningResult = document.getElementById('warningResult');
    const warningList = document.getElementById('warningList');
    const safeResult = document.getElementById('safeResult');
    const warningDay = document.getElementById('warningDay');
    const warningHub = document.getElementById('warningHub');
    const warningPlotContainer = document.getElementById('warningPlotContainer');
    const warningPlot = document.getElementById('warningPlot');
    const warningTablesContainer = document.getElementById('warningTablesContainer');
    const warningPrimaryTableBody = document.getElementById('warningPrimaryTableBody');
    const warningSecondaryTableBody = document.getElementById('warningSecondaryTableBody');
    
    function addTrajectoryRow(t = 24, x = 100, y = 75) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="number" class="form-control form-control-sm traj-t" value="${t}" min="1" max="48"></td>
            <td><input type="number" class="form-control form-control-sm traj-x" value="${x}"></td>
            <td><input type="number" class="form-control form-control-sm traj-y" value="${y}"></td>
            <td><button class="btn btn-sm btn-danger w-100" onclick="this.closest('tr').remove()">刪除</button></td>
        `;
        trajectoryBody.appendChild(tr);
    }
    
    if (addTrajBtn) {
        addTrajBtn.addEventListener('click', () => addTrajectoryRow());
        
        checkWarningBtn.addEventListener('click', async () => {
            const eventDay = warningDay.value;
            const selectedOptions = Array.from(warningHub.selectedOptions).map(opt => parseInt(opt.value));
            if (selectedOptions.length === 0) {
                alert("請至少選擇一個假設事件 Hub！");
                return;
            }
            
            const rows = trajectoryBody.querySelectorAll('tr');
            const trajectory = [];
            
            rows.forEach(r => {
                const t = r.querySelector('.traj-t').value;
                const x = r.querySelector('.traj-x').value;
                const y = r.querySelector('.traj-y').value;
                if(t && x && y) {
                    trajectory.push({
                        d: parseInt(eventDay),
                        time: parseInt(t),
                        x: parseFloat(x),
                        y: parseFloat(y)
                    });
                }
            });
            
            checkWarningBtn.disabled = true;
            checkWarningBtn.textContent = '檢查中...';
            warningResult.style.display = 'none';
            safeResult.style.display = 'none';
            warningPlotContainer.style.display = 'none';
            warningList.innerHTML = '';
            if (warningTablesContainer) {
                warningTablesContainer.style.display = 'none';
                warningPrimaryTableBody.innerHTML = '';
                warningSecondaryTableBody.innerHTML = '';
            }
            
            try {
                const res = await fetch('/api/check_warning', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ trajectory, eventDay: parseInt(eventDay), eventHubs: selectedOptions })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    const distText = data.overall_min_dist !== null ? `距任一事件 Hub 最近距離：${data.overall_min_dist}` : '';
                    
                    if (data.warnings.length > 0) {
                        warningResult.style.display = 'block';
                        let html = '';
                        if (distText) {
                            html += `<li style="font-weight:bold; list-style:none; margin-bottom:10px; color:var(--crimson);">${distText}</li>`;
                        }
                        data.warnings.forEach(w => {
                            html += `<li>${w.message}</li>`;
                        });
                        warningList.innerHTML = html;
                    } else {
                        safeResult.style.display = 'block';
                        if (distText) {
                            safeResult.innerHTML = `<h3 style="margin-bottom: 5px; color: #16a34a;">安全：未偵測到高風險足跡重疊。</h3><p style="margin:0; color:#16a34a; font-size:0.875rem;">${distText}</p>`;
                        } else {
                            safeResult.innerHTML = `<h3 style="margin-bottom: 0; color: #16a34a;">安全：未偵測到高風險足跡重疊。</h3>`;
                        }
                    }
                    
                    if (data.warning_plot) {
                        warningPlot.src = data.warning_plot;
                        warningPlotContainer.style.display = 'block';
                    }
                    
                    if (warningTablesContainer) {
                        warningTablesContainer.style.display = 'block';
                        
                        if (data.primary_users && data.primary_users.length > 0) {
                            data.primary_users.forEach(u => {
                                const tr = document.createElement('tr');
                                tr.innerHTML = `
                                    <td>${u.uid}</td>
                                    <td>G${u.hub}</td>
                                    <td>${u.time}</td>
                                `;
                                warningPrimaryTableBody.appendChild(tr);
                            });
                        } else {
                            warningPrimaryTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">無直接影響使用者</td></tr>';
                        }
                        
                        if (data.secondary_users && data.secondary_users.length > 0) {
                            data.secondary_users.forEach(u => {
                                const tr = document.createElement('tr');
                                tr.innerHTML = `
                                    <td>${u.uid}</td>
                                    <td>G${u.hub}</td>
                                    <td>${u.time}</td>
                                `;
                                warningSecondaryTableBody.appendChild(tr);
                            });
                        } else {
                            warningSecondaryTableBody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted);">無間接影響使用者</td></tr>';
                        }
                    }
                } else {
                    alert('檢查失敗: ' + (data.error || '未知錯誤'));
                }
            } catch(err) {
                console.error(err);
                alert('風險檢查失敗');
            } finally {
                checkWarningBtn.disabled = false;
                checkWarningBtn.textContent = '檢查風險';
            }
        });
    }

    // ==========================================
    // Traffic Analysis Logic
    // ==========================================
    let trafficChartInstance = null;
    const analyzeTrafficBtn = document.getElementById('analyzeTrafficBtn');
    
    if (analyzeTrafficBtn) {
        analyzeTrafficBtn.addEventListener('click', async () => {
            const day = parseInt(document.getElementById('trafficDay').value);
            const hub = parseInt(document.getElementById('trafficHub').value);
            const tStart = parseInt(document.getElementById('trafficStart').value);
            const tEnd = parseInt(document.getElementById('trafficEnd').value);
            
            if(tStart > tEnd) {
                alert('時間區間起點必須小於或等於終點。');
                return;
            }
            
            showLoader('分析交通影響中...');
            try {
                const response = await fetch('/api/trace_cascade', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ day, hub, tStart, tEnd, isTrafficTab: true })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    const timeCountsPrimary = {};
                    const allUsers = [];
                    
                    data.primary_users.forEach(u => {
                        timeCountsPrimary[u.time] = (timeCountsPrimary[u.time] || 0) + 1;
                        allUsers.push({ ...u, level: '被阻斷 (Blocked)' });
                    });
                    
                    allUsers.sort((a, b) => a.time.localeCompare(b.time));
                    
                    const tbody = document.getElementById('trafficTableBody');
                    tbody.innerHTML = '';
                    if (allUsers.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">無受影響資料</td></tr>';
                    } else {
                        allUsers.forEach(u => {
                            const tr = document.createElement('tr');
                            tr.innerHTML = `
                                <td>${u.uid}</td>
                                <td>${u.time}</td>
                                <td>G${u.hub}</td>
                                <td><span style="color: var(--crimson)">${u.level}</span></td>
                            `;
                            tbody.appendChild(tr);
                        });
                    }
                    
                    const allTimesSet = new Set(Object.keys(timeCountsPrimary));
                    const sortedTimes = Array.from(allTimesSet).sort();
                    
                    const primaryCounts = sortedTimes.map(t => timeCountsPrimary[t] || 0);
                    
                    const ctx = document.getElementById('trafficChart').getContext('2d');
                    if (trafficChartInstance) {
                        trafficChartInstance.destroy();
                    }
                    
                    trafficChartInstance = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: sortedTimes,
                            datasets: [
                                {
                                    label: '經過並被阻斷人數',
                                    data: primaryCounts,
                                    backgroundColor: 'rgba(220, 38, 38, 0.9)', // Red
                                    borderColor: 'rgba(220, 38, 38, 1)',
                                    borderWidth: 1
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                x: {
                                    stacked: true,
                                    title: { display: true, text: '影響時間' }
                                },
                                y: {
                                    stacked: true,
                                    beginAtZero: true,
                                    title: { display: true, text: '受影響人數' }
                                }
                            }
                        }
                    });
                    
                    if (data.impact_plot_paths) {
                        document.getElementById('trafficPlot').src = data.impact_plot_paths;
                        document.getElementById('trafficPlotContainer').style.display = 'block';
                    } else {
                        document.getElementById('trafficPlotContainer').style.display = 'none';
                    }
                }
            } catch(err) {
                console.error(err);
                alert('交通影響分析失敗');
            } finally {
                hideLoader();
            }
        });
    }
});
