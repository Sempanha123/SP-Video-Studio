import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import "../theme"
import "../components"
Item { id: root; property var controller; signal itemSelected(var itemData)
    ColumnLayout { anchors.fill: parent; spacing: Theme.spacing.sm
        RowLayout { Layout.fillWidth: true; spacing: Theme.spacing.sm
            AppComboBox { id: filter; Layout.preferredWidth: 136; model: ["all","running","pending","completed","failed","skipped"]; onActivated: controller.setQueueFilter(currentText, search.text) }
            SearchField { id: search; Layout.fillWidth: true; placeholderText: "Search item, key or output"; onTextChanged: controller.setQueueFilter(filter.currentText,text); onClearRequested: controller.setQueueFilter(filter.currentText,"") }
            AppButton { text: "Retry Failed"; variant: "secondary"; size: "small"; onClicked: controller.retryAllFailed() }
        }
        ListView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 2; reuseItems: true; cacheBuffer: 480; model: controller ? controller.items : []
            delegate: BatchItemRow { width: ListView.view.width; itemData: modelData; controller: root.controller; onSelected: root.itemSelected(data) }
        }
    }
}
