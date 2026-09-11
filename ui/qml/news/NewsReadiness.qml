import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"

AppCard {
    id:root; property var overview:({})
    ColumnLayout { anchors.fill:parent; anchors.margins:Theme.spacing.lg; spacing:Theme.spacing.md
        RowLayout { Layout.fillWidth:true; Text { Layout.fillWidth:true; text:"Production Readiness"; color:Theme.colors.textPrimary; font.pixelSize:Theme.type.heading; font.weight:Theme.type.semibold }; StatusBadge { text:(root.overview.level||"not_ready").replace(/_/g," "); status:root.overview.level==="ready_for_production"?"ready":(root.overview.level==="not_ready"?"offline":"warning") } }
        Text { text:(root.overview.sources||0)+" sources · "+(root.overview.approvedClaims||0)+" approved claims"; color:Theme.colors.textSecondary }
        Text { text:(root.overview.needsReviewClaims||0)+" need review · "+(root.overview.conflictingClaims||0)+" conflicting · "+(root.overview.unsupportedClaims||0)+" unsupported"; color:Theme.colors.textMuted }
        Text { text:"Readiness measures workflow review state, not a truth score."; color:Theme.colors.textMuted; font.pixelSize:Theme.type.caption }
    }
}
