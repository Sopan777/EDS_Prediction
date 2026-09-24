document.addEventListener("DOMContentLoaded", function () {

    /* ==========================================
       KPI COUNTER ANIMATION
       ========================================== */

    document.querySelectorAll(".counter").forEach(function (counter) {

        const target = Number(counter.dataset.target || 0);

        let current = 0;

        const duration = 700;

        const startTime = performance.now();


        function animate(now) {

            const progress =
                Math.min(
                    (now - startTime) / duration,
                    1
                );


            current = Math.floor(
                target *
                (1 - Math.pow(1 - progress, 3))
            );


            counter.textContent =
                current.toLocaleString();


            if (progress < 1) {

                requestAnimationFrame(animate);

            }

        }


        requestAnimationFrame(animate);

    });


    /* ==========================================
       DASHBOARD DATA
       ========================================== */

    const dashboard =
        window.WSA_DASHBOARD;


    if (!dashboard) {

        console.warn(
            "WSA dashboard data was not found."
        );

        return;

    }


    /* ==========================================
       CANVAS HELPERS
       ========================================== */

    function prepareCanvas(canvas) {

        if (!canvas) {
            return null;
        }


        const rect =
            canvas.getBoundingClientRect();


        const dpr =
            window.devicePixelRatio || 1;


        canvas.width =
            Math.max(
                1,
                Math.floor(rect.width * dpr)
            );


        canvas.height =
            Math.max(
                1,
                Math.floor(rect.height * dpr)
            );


        const ctx =
            canvas.getContext("2d");


        ctx.setTransform(
            dpr,
            0,
            0,
            dpr,
            0,
            0
        );


        ctx.clearRect(
            0,
            0,
            rect.width,
            rect.height
        );


        return {
            ctx: ctx,
            width: rect.width,
            height: rect.height
        };

    }


    function drawText(
        ctx,
        text,
        x,
        y,
        size,
        color,
        align = "left"
    ) {

        ctx.font =
            `${size}px Poppins, Arial, sans-serif`;

        ctx.fillStyle =
            color;

        ctx.textAlign =
            align;

        ctx.textBaseline =
            "middle";

        ctx.fillText(
            String(text),
            x,
            y
        );

    }


    function roundedRect(
        ctx,
        x,
        y,
        width,
        height,
        radius
    ) {

        const r =
            Math.min(
                radius,
                width / 2,
                height / 2
            );


        ctx.beginPath();

        ctx.moveTo(
            x + r,
            y
        );

        ctx.arcTo(
            x + width,
            y,
            x + width,
            y + height,
            r
        );

        ctx.arcTo(
            x + width,
            y + height,
            x,
            y + height,
            r
        );

        ctx.arcTo(
            x,
            y + height,
            x,
            y,
            r
        );

        ctx.arcTo(
            x,
            y,
            x + width,
            y,
            r
        );

        ctx.closePath();

    }


    /* ==========================================
       DAILY AUDIT VS NOK LINE CHART
       ========================================== */

    function drawLineChart() {

        const canvas =
            document.getElementById(
                "dailyTrendChart"
            );


        const prepared =
            prepareCanvas(canvas);


        if (!prepared) {
            return;
        }


        const ctx =
            prepared.ctx;

        const width =
            prepared.width;

        const height =
            prepared.height;


        const labels =
            dashboard.dailyLabels || [];

        const audits =
            dashboard.dailyAudits || [];

        const nok =
            dashboard.dailyNok || [];


        if (
            labels.length === 0 ||
            audits.length === 0
        ) {

            drawText(
                ctx,
                "No data available",
                width / 2,
                height / 2,
                13,
                "#6b7280",
                "center"
            );

            return;

        }


        const left =
            58;

        const right =
            20;

        const top =
            28;

        const bottom =
            48;


        const chartWidth =
            width - left - right;

        const chartHeight =
            height - top - bottom;


        const maxValue =
            Math.max(
                ...audits,
                ...nok,
                1
            );


        /* GRID */

        ctx.strokeStyle =
            "#e8edf5";

        ctx.lineWidth =
            1;


        const gridLines = 5;


        for (
            let i = 0;
            i <= gridLines;
            i++
        ) {

            const y =
                top +
                chartHeight *
                (i / gridLines);


            ctx.beginPath();

            ctx.moveTo(
                left,
                y
            );

            ctx.lineTo(
                width - right,
                y
            );

            ctx.stroke();


            const value =
                Math.round(
                    maxValue *
                    (1 - i / gridLines)
                );


            drawText(
                ctx,
                value,
                left - 10,
                y,
                9,
                "#7b8494",
                "right"
            );

        }


        /* X LABELS */

        const step =
            labels.length > 1
                ? chartWidth / (labels.length - 1)
                : chartWidth;


        labels.forEach(
            function (label, index) {

                const x =
                    labels.length > 1
                        ? left + index * step
                        : left + chartWidth / 2;


                drawText(
                    ctx,
                    label,
                    x,
                    height - 18,
                    9,
                    "#7b8494",
                    "center"
                );

            }
        );


        /* LEGEND */

        ctx.fillStyle =
            "#0A1F44";

        ctx.fillRect(
            left,
            5,
            10,
            3
        );


        drawText(
            ctx,
            "Audits",
            left + 16,
            7,
            9,
            "#4b5563",
            "left"
        );


        ctx.fillStyle =
            "#DC3545";

        ctx.fillRect(
            left + 75,
            5,
            10,
            3
        );


        drawText(
            ctx,
            "NOK",
            left + 91,
            7,
            9,
            "#4b5563",
            "left"
        );


        /* LINE FUNCTION */

        function drawSeries(
            values,
            strokeColor,
            fillColor
        ) {

            if (!values.length) {
                return;
            }


            const points =
                values.map(
                    function (value, index) {

                        const x =
                            values.length > 1
                                ? left + index * step
                                : left + chartWidth / 2;


                        const y =
                            top +
                            chartHeight -
                            (
                                (Number(value) / maxValue)
                                * chartHeight
                            );


                        return {
                            x: x,
                            y: y
                        };

                    }
                );


            /* FILL */

            ctx.beginPath();

            ctx.moveTo(
                points[0].x,
                top + chartHeight
            );


            points.forEach(
                function (point) {

                    ctx.lineTo(
                        point.x,
                        point.y
                    );

                }
            );


            ctx.lineTo(
                points[points.length - 1].x,
                top + chartHeight
            );


            ctx.closePath();

            ctx.fillStyle =
                fillColor;

            ctx.fill();


            /* LINE */

            ctx.beginPath();


            points.forEach(
                function (point, index) {

                    if (index === 0) {

                        ctx.moveTo(
                            point.x,
                            point.y
                        );

                    } else {

                        ctx.lineTo(
                            point.x,
                            point.y
                        );

                    }

                }
            );


            ctx.strokeStyle =
                strokeColor;

            ctx.lineWidth =
                3;

            ctx.lineJoin =
                "round";

            ctx.lineCap =
                "round";

            ctx.stroke();


            /* POINTS */

            points.forEach(
                function (point) {

                    ctx.beginPath();

                    ctx.arc(
                        point.x,
                        point.y,
                        4,
                        0,
                        Math.PI * 2
                    );

                    ctx.fillStyle =
                        "#ffffff";

                    ctx.fill();

                    ctx.strokeStyle =
                        strokeColor;

                    ctx.lineWidth =
                        2;

                    ctx.stroke();

                }
            );

        }


        drawSeries(
            audits,
            "#0A1F44",
            "rgba(10,31,68,0.07)"
        );


        drawSeries(
            nok,
            "#DC3545",
            "rgba(220,53,69,0.07)"
        );

    }


    /* ==========================================
       SHIFT PERFORMANCE DOUGHNUT
       ========================================== */

    function drawShiftChart() {

        const canvas =
            document.getElementById(
                "shiftChart"
            );


        const prepared =
            prepareCanvas(canvas);


        if (!prepared) {
            return;
        }


        const ctx =
            prepared.ctx;

        const width =
            prepared.width;

        const height =
            prepared.height;


        const labels =
            dashboard.shiftLabels || [];

        const values =
            dashboard.shiftNok || [];


        if (!labels.length) {

            drawText(
                ctx,
                "No shift data available",
                width / 2,
                height / 2,
                13,
                "#6b7280",
                "center"
            );

            return;

        }


        const total =
            values.reduce(
                function (sum, value) {

                    return sum +
                        Number(value || 0);

                },
                0
            );


        const centerX =
            width / 2;

        const centerY =
            height / 2 - 12;


        const radius =
            Math.min(
                width,
                height
            ) * 0.28;


        const innerRadius =
            radius * 0.62;


        const colors = [
            "#0A1F44",
            "#2F80ED",
            "#6C63FF",
            "#17824B",
            "#DC3545"
        ];


        if (total === 0) {

            ctx.beginPath();

            ctx.arc(
                centerX,
                centerY,
                radius,
                0,
                Math.PI * 2
            );

            ctx.fillStyle =
                "#e8edf5";

            ctx.fill();

        } else {

            let startAngle =
                -Math.PI / 2;


            values.forEach(
                function (value, index) {

                    const numericValue =
                        Number(value || 0);


                    if (numericValue <= 0) {
                        return;
                    }


                    const angle =
                        (
                            numericValue /
                            total
                        ) *
                        Math.PI *
                        2;


                    ctx.beginPath();

                    ctx.moveTo(
                        centerX,
                        centerY
                    );


                    ctx.arc(
                        centerX,
                        centerY,
                        radius,
                        startAngle,
                        startAngle + angle
                    );


                    ctx.closePath();


                    ctx.fillStyle =
                        colors[
                            index % colors.length
                        ];


                    ctx.fill();


                    startAngle += angle;

                }
            );

        }


        /* INNER CIRCLE */

        ctx.beginPath();

        ctx.arc(
            centerX,
            centerY,
            innerRadius,
            0,
            Math.PI * 2
        );

        ctx.fillStyle =
            "#ffffff";

        ctx.fill();


        drawText(
            ctx,
            total,
            centerX,
            centerY - 5,
            22,
            "#0A1F44",
            "center"
        );


        drawText(
            ctx,
            "NOK",
            centerX,
            centerY + 18,
            9,
            "#6b7280",
            "center"
        );


        /* LEGEND */

        const legendTop =
            centerY + radius + 18;


        labels.forEach(
            function (label, index) {

                const x =
                    20 +
                    (
                        index %
                        2
                    ) *
                    (width / 2);


                const y =
                    legendTop +
                    Math.floor(index / 2) * 22;


                ctx.fillStyle =
                    colors[
                        index % colors.length
                    ];


                ctx.fillRect(
                    x,
                    y - 5,
                    10,
                    10
                );


                drawText(
                    ctx,
                    `${label} (${values[index] || 0})`,
                    x + 17,
                    y,
                    9,
                    "#4b5563",
                    "left"
                );

            }
        );

    }


    /* ==========================================
       LINE-WISE NOK BAR CHART
       ========================================== */

    function drawLineChartBars() {

        const canvas =
            document.getElementById(
                "lineChart"
            );


        const prepared =
            prepareCanvas(canvas);


        if (!prepared) {
            return;
        }


        const ctx =
            prepared.ctx;

        const width =
            prepared.width;

        const height =
            prepared.height;


        const labels =
            dashboard.lineLabels || [];

        const values =
            dashboard.lineNok || [];


        if (!labels.length) {

            drawText(
                ctx,
                "No line data available",
                width / 2,
                height / 2,
                13,
                "#6b7280",
                "center"
            );

            return;

        }


        const left =
            48;

        const right =
            20;

        const top =
            25;

        const bottom =
            50;


        const chartWidth =
            width - left - right;

        const chartHeight =
            height - top - bottom;


        const maxValue =
            Math.max(
                ...values.map(
                    function (v) {
                        return Number(v || 0);
                    }
                ),
                1
            );


        const slotWidth =
            chartWidth /
            labels.length;


        const barWidth =
            Math.min(
                55,
                slotWidth * 0.55
            );


        /* GRID */

        const gridLines =
            5;


        ctx.strokeStyle =
            "#e8edf5";

        ctx.lineWidth =
            1;


        for (
            let i = 0;
            i <= gridLines;
            i++
        ) {

            const y =
                top +
                chartHeight *
                (i / gridLines);


            ctx.beginPath();

            ctx.moveTo(
                left,
                y
            );

            ctx.lineTo(
                width - right,
                y
            );

            ctx.stroke();


            const value =
                Math.round(
                    maxValue *
                    (1 - i / gridLines)
                );


            drawText(
                ctx,
                value,
                left - 9,
                y,
                9,
                "#7b8494",
                "right"
            );

        }


        /* BARS */

        values.forEach(
            function (value, index) {

                const numericValue =
                    Number(value || 0);


                const barHeight =
                    (
                        numericValue /
                        maxValue
                    ) *
                    chartHeight;


                const x =
                    left +
                    index * slotWidth +
                    (
                        slotWidth -
                        barWidth
                    ) / 2;


                const y =
                    top +
                    chartHeight -
                    barHeight;


                roundedRect(
                    ctx,
                    x,
                    y,
                    barWidth,
                    Math.max(
                        barHeight,
                        2
                    ),
                    7
                );


                ctx.fillStyle =
                    "#0052D4";

                ctx.fill();


                drawText(
                    ctx,
                    numericValue,
                    x + barWidth / 2,
                    y - 10,
                    9,
                    "#0A1F44",
                    "center"
                );


                drawText(
                    ctx,
                    labels[index],
                    x + barWidth / 2,
                    height - 20,
                    9,
                    "#6b7280",
                    "center"
                );

            }
        );

    }


    /* ==========================================
       INITIAL DRAW
       ========================================== */

    drawLineChart();

    drawShiftChart();

    drawLineChartBars();


    /* ==========================================
       REDRAW ON RESIZE
       ========================================== */

    let resizeTimer;


    window.addEventListener(
        "resize",
        function () {

            clearTimeout(
                resizeTimer
            );


            resizeTimer =
                setTimeout(
                    function () {

                        drawLineChart();

                        drawShiftChart();

                        drawLineChartBars();

                    },
                    200
                );

        }
    );

});